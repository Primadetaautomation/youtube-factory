"""YouTube Factory - Streamlit UI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from config import (
    OPENAI_API_KEY, ELEVENLABS_API_KEY, YOUTUBE_API_KEY,
    OUTPUT_DIR, TEMP_DIR,
)
from steps.script_generator import generate_script, refine_script
from steps.voiceover import generate_voiceover, get_audio_duration
from steps.clip_finder import search_clips_for_scenes, download_selected_clips
from steps.video_editor import combine_clips, add_audio_to_video
from steps.thumbnail import generate_thumbnail
from steps.metadata import generate_metadata

# --- Page Config ---
st.set_page_config(
    page_title="YouTube Factory",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 1rem;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 { color: white; font-size: 2.5rem; margin: 0; }
    .main-header p { color: rgba(255,255,255,0.8); font-size: 1.1rem; }
    .clip-card {
        background: #1a1d23;
        border: 1px solid #2d3139;
        border-radius: 0.5rem;
        padding: 0.5rem;
        text-align: center;
    }
    .clip-card.selected { border-color: #667eea; box-shadow: 0 0 10px rgba(102,126,234,0.4); }
</style>
""", unsafe_allow_html=True)

# --- Session State defaults ---
DEFAULTS = {
    "step": 0, "script_data": None, "audio_path": None,
    "visuals_data": None, "clips": [], "final_video": None,
    "thumbnail_path": None, "metadata": None,
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- Header ---
st.markdown("""
<div class="main-header">
    <h1>YouTube Factory</h1>
    <p>Onderwerp invoeren → Video op YouTube. Volledig geautomatiseerd.</p>
</div>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("### Settings")

    st.markdown("**API Status:**")
    for name, key in [("OpenAI", OPENAI_API_KEY), ("ElevenLabs", ELEVENLABS_API_KEY), ("YouTube", YOUTUBE_API_KEY)]:
        if key:
            st.success(f"{name} ✓")
        else:
            st.error(f"{name} ✗")

    st.divider()

    st.markdown("### Pipeline")
    steps_list = [
        "Script genereren",
        "Script reviewen",
        "Voiceover maken",
        "Clips zoeken & kiezen",
        "Clips downloaden",
        "Video samenstellen",
        "Thumbnail & metadata",
        "Uploaden",
    ]
    for i, step_name in enumerate(steps_list):
        if i < st.session_state.step:
            st.markdown(f"✅ ~~{step_name}~~")
        elif i == st.session_state.step:
            st.markdown(f"▶️ **{step_name}**")
        else:
            st.markdown(f"⬜ {step_name}")

    st.divider()
    if st.button("Reset pipeline", use_container_width=True):
        for key, val in DEFAULTS.items():
            st.session_state[key] = [] if isinstance(val, list) else val
        st.rerun()


# =============================================
# STEP 0 — Onderwerp invoeren
# =============================================
if st.session_state.step == 0:
    st.markdown("### Stap 1: Kies je onderwerp")

    col1, col2 = st.columns([3, 1])
    with col1:
        topic = st.text_input(
            "Onderwerp",
            placeholder="bijv. Carlos Alcaraz, Lionel Messi, Max Verstappen...",
            label_visibility="collapsed",
        )
    with col2:
        duration = st.selectbox("Duur", [3, 4, 5, 6], index=1, format_func=lambda x: f"{x} min")

    if st.button("Genereer Script", use_container_width=True, type="primary", disabled=not topic):
        with st.spinner("Script wordt gegenereerd door AI..."):
            try:
                script_data = generate_script(topic, duration)
                st.session_state.script_data = script_data
                st.session_state.topic = topic
                st.session_state.duration = duration
                st.session_state.step = 1
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij script generatie: {e}")


# =============================================
# STEP 1 — Script reviewen & aanpassen
# =============================================
elif st.session_state.step == 1:
    st.markdown("### Stap 2: Script bekijken & aanpassen")

    script_data = st.session_state.script_data
    tab1, tab2 = st.tabs(["Script", "Scenes & Visuals"])

    with tab1:
        edited_script = st.text_area(
            "Script (pas aan indien nodig)",
            value=script_data.get("script", ""),
            height=400,
        )
        feedback = st.text_input("Feedback voor AI (optioneel)", placeholder="Maak het dramatischer...")
        if st.button("Verfijn met AI") and feedback:
            with st.spinner("Script wordt verfijnd..."):
                refined = refine_script(edited_script, feedback)
                st.session_state.script_data = refined
                st.rerun()

    with tab2:
        for i, scene in enumerate(script_data.get("scenes", [])):
            with st.expander(f"Scene {i+1}: {scene.get('section', '')} ({scene.get('timestamp', '')})"):
                st.markdown(f"**Narration:** {scene.get('narration', '')}")
                for v in scene.get("visuals", []):
                    st.markdown(f"- `{v.get('search_query', '')}` — {v.get('description', '')}")

    if edited_script != script_data.get("script", ""):
        st.session_state.script_data["script"] = edited_script

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Terug"):
            st.session_state.step = 0
            st.rerun()
    with col2:
        if st.button("Voiceover genereren", type="primary", use_container_width=True):
            st.session_state.step = 2
            st.rerun()


# =============================================
# STEP 2 — Voiceover
# =============================================
elif st.session_state.step == 2:
    st.markdown("### Stap 3: Voiceover genereren")

    if st.session_state.audio_path is None:
        with st.spinner("Voiceover wordt gegenereerd met ElevenLabs..."):
            try:
                script_text = st.session_state.script_data.get("script", "")
                safe_name = st.session_state.topic.lower().replace(" ", "_")[:30]
                audio_path = generate_voiceover(script_text, safe_name)
                dur = get_audio_duration(audio_path)
                st.session_state.audio_path = audio_path
                st.session_state.audio_duration = dur
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij voiceover: {e}")
                if st.button("Terug"):
                    st.session_state.step = 1
                    st.rerun()
    else:
        st.success(f"Voiceover klaar! Duur: {st.session_state.audio_duration:.1f} seconden")
        st.audio(str(st.session_state.audio_path))

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Terug"):
                st.session_state.step = 1
                st.session_state.audio_path = None
                st.rerun()
        with col2:
            if st.button("Opnieuw genereren"):
                st.session_state.audio_path = None
                st.rerun()
        with col3:
            if st.button("Clips zoeken", type="primary", use_container_width=True):
                st.session_state.step = 3
                st.rerun()


# =============================================
# STEP 3 — Clips zoeken & kiezen (NIEUW!)
# =============================================
elif st.session_state.step == 3:
    st.markdown("### Stap 4: Clips zoeken & kiezen")
    st.markdown("Per scriptregel zie je 5 YouTube resultaten. **Kies de beste clip per regel.**")

    # Search if not done yet
    if st.session_state.visuals_data is None:
        with st.spinner("YouTube wordt doorzocht voor elke scene..."):
            try:
                scenes = st.session_state.script_data.get("scenes", [])
                visuals_data = search_clips_for_scenes(scenes, results_per_query=5)
                st.session_state.visuals_data = visuals_data
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij zoeken: {e}")
                if st.button("Terug"):
                    st.session_state.step = 2
                    st.rerun()
    else:
        visuals_data = st.session_state.visuals_data

        for vi, visual in enumerate(visuals_data):
            st.divider()
            st.markdown(f"**Clip {vi+1}:** _{visual['description']}_")
            st.caption(f"Zoekopdracht: `{visual['search_query']}`")

            options = visual.get("options", [])
            if not options:
                st.warning("Geen resultaten gevonden")
                continue

            cols = st.columns(min(len(options), 5))
            for oi, option in enumerate(options):
                with cols[oi]:
                    st.image(option["thumbnail"], use_container_width=True)
                    st.caption(f"{option['title'][:45]}...")
                    st.caption(f"_{option['channel']}_")

            # Selection radio
            titles = [f"{o['title'][:50]}" for o in options]
            current = visual.get("selected_index", 0)
            selected = st.radio(
                f"Kies clip voor: {visual['description'][:60]}",
                range(len(titles)),
                index=current,
                format_func=lambda x, t=titles: t[x],
                key=f"clip_select_{vi}",
                horizontal=True,
                label_visibility="collapsed",
            )
            st.session_state.visuals_data[vi]["selected_index"] = selected

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Terug"):
                st.session_state.step = 2
                st.session_state.visuals_data = None
                st.rerun()
        with col2:
            if st.button("Download geselecteerde clips", type="primary", use_container_width=True):
                st.session_state.step = 4
                st.rerun()


# =============================================
# STEP 4 — Clips downloaden
# =============================================
elif st.session_state.step == 4:
    st.markdown("### Stap 5: Geselecteerde clips downloaden")

    if not st.session_state.clips:
        visuals = st.session_state.visuals_data
        total = len(visuals)

        progress_bar = st.progress(0)
        status_text = st.empty()
        log = st.empty()

        clips = []
        log_lines = []

        for i, visual in enumerate(visuals):
            selected = visual.get("selected_index", 0)
            options = visual.get("options", [])
            if not options or selected >= len(options):
                continue

            option = options[selected]
            status_text.markdown(f"**Downloading {i+1}/{total}:** {option['title'][:60]}")
            progress_bar.progress((i + 1) / max(total, 1))

            from steps.clip_finder import download_clip
            clip_path = download_clip(option["url"], i)

            if clip_path:
                clips.append(clip_path)
                log_lines.append(f"✅ {option['title'][:60]}")
            else:
                log_lines.append(f"❌ {option['title'][:60]}")

            log.markdown("\n\n".join(log_lines))

        st.session_state.clips = clips
        progress_bar.progress(1.0)
        status_text.markdown(f"**Klaar!** {len(clips)}/{total} clips gedownload")
    else:
        st.success(f"{len(st.session_state.clips)} clips gedownload en opgeslagen in `temp/`")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Terug (opnieuw kiezen)"):
            st.session_state.step = 3
            st.session_state.clips = []
            st.rerun()
    with col2:
        if st.button("Video samenstellen", type="primary", use_container_width=True, disabled=not st.session_state.clips):
            st.session_state.step = 5
            st.rerun()


# =============================================
# STEP 5 — Video samenstellen
# =============================================
elif st.session_state.step == 5:
    st.markdown("### Stap 6: Video samenstellen")

    if st.session_state.final_video is None:
        with st.spinner("Clips worden gecombineerd met voiceover..."):
            try:
                combined = combine_clips(st.session_state.clips, st.session_state.audio_duration)
                safe_name = st.session_state.topic.lower().replace(" ", "_")[:30]
                final = add_audio_to_video(combined, st.session_state.audio_path, safe_name)
                st.session_state.final_video = final
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij video editing: {e}")
                if st.button("Terug"):
                    st.session_state.step = 4
                    st.rerun()
    else:
        st.success("Video samengesteld!")
        st.video(str(st.session_state.final_video))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Terug"):
                st.session_state.step = 4
                st.session_state.final_video = None
                st.rerun()
        with col2:
            if st.button("Thumbnail + Metadata", type="primary", use_container_width=True):
                st.session_state.step = 6
                st.rerun()


# =============================================
# STEP 6 — Thumbnail & Metadata
# =============================================
elif st.session_state.step == 6:
    st.markdown("### Stap 7: Thumbnail & Metadata")

    col_thumb, col_meta = st.columns(2)

    with col_thumb:
        st.markdown("**Thumbnail**")
        if st.session_state.thumbnail_path is None:
            with st.spinner("Thumbnail wordt gegenereerd..."):
                try:
                    safe_name = st.session_state.topic.lower().replace(" ", "_")[:30]
                    meta = generate_metadata(
                        st.session_state.topic,
                        st.session_state.script_data.get("script", ""),
                    )
                    st.session_state.metadata = meta
                    thumb = generate_thumbnail(st.session_state.topic, meta["title"], safe_name)
                    st.session_state.thumbnail_path = thumb
                    st.rerun()
                except Exception as e:
                    st.error(f"Fout bij thumbnail: {e}")
        else:
            st.image(str(st.session_state.thumbnail_path), use_container_width=True)
            if st.button("Nieuwe thumbnail"):
                st.session_state.thumbnail_path = None
                st.rerun()

    with col_meta:
        st.markdown("**Metadata**")
        if st.session_state.metadata:
            meta = st.session_state.metadata
            new_title = st.text_input("Titel", value=meta.get("title", ""))
            new_desc = st.text_area("Beschrijving", value=meta.get("description", ""), height=200)
            new_tags = st.text_input("Tags (komma-gescheiden)", value=", ".join(meta.get("tags", [])))

            st.session_state.metadata["title"] = new_title
            st.session_state.metadata["description"] = new_desc
            st.session_state.metadata["tags"] = [t.strip() for t in new_tags.split(",")]

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Terug"):
            st.session_state.step = 5
            st.rerun()
    with col2:
        privacy = st.selectbox("Privacy", ["private", "unlisted", "public"])
        if st.button("Upload naar YouTube", type="primary", use_container_width=True):
            st.session_state.privacy = privacy
            st.session_state.step = 7
            st.rerun()

    # Local download option
    if st.session_state.final_video and st.session_state.final_video.exists():
        with open(st.session_state.final_video, "rb") as f:
            st.download_button(
                "Download video lokaal (skip upload)",
                f,
                file_name=f"{st.session_state.topic}.mp4",
                mime="video/mp4",
            )


# =============================================
# STEP 7 — Upload naar YouTube
# =============================================
elif st.session_state.step == 7:
    st.markdown("### Stap 8: Uploaden naar YouTube")

    with st.spinner("Video wordt geupload..."):
        try:
            from steps.uploader import upload_video
            video_id = upload_video(
                st.session_state.final_video,
                st.session_state.metadata["title"],
                st.session_state.metadata["description"],
                st.session_state.metadata["tags"],
                st.session_state.thumbnail_path,
                st.session_state.get("privacy", "private"),
            )
            st.balloons()
            st.success("Video geupload!")
            st.markdown(f"### [Bekijk op YouTube](https://youtu.be/{video_id})")

        except FileNotFoundError:
            st.warning("`client_secret.json` niet gevonden.")
            st.markdown("""
            **Setup:**
            1. [Google Cloud Console](https://console.cloud.google.com) → Credentials
            2. Create OAuth client ID → Desktop app
            3. Download JSON → hernoem naar `client_secret.json`
            4. Zet in `youtube-factory/` folder
            """)
        except Exception as e:
            st.error(f"Upload fout: {e}")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Terug naar metadata"):
            st.session_state.step = 6
            st.rerun()
    with col2:
        if st.button("Nieuwe video maken", use_container_width=True):
            for key, val in DEFAULTS.items():
                st.session_state[key] = [] if isinstance(val, list) else val
            st.rerun()
