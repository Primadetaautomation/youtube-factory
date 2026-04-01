"""End-to-end browser tests for YouTube Factory UI."""

import sys
from playwright.sync_api import sync_playwright

ERRORS = []
PASSED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  PASS: {name}")
    else:
        ERRORS.append(name)
        print(f"  FAIL: {name} {detail}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # ── 1. Homepage loads ──
        print("\n== 1. Homepage ==")
        page.goto("http://localhost:3333")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="/tmp/yt_e2e_01_homepage.png", full_page=True)

        check("Page loads", page.title() != "")
        check("Mode buttons visible",
              page.locator("button.mode-btn").count() >= 4)
        check("Video mode active",
              "active" in (page.locator("#modeSingle").get_attribute("class") or ""))

        # ── 2. Settings panel ──
        print("\n== 2. Settings Panel ==")
        settings = page.locator("details.settings-panel")
        check("Settings panel exists", settings.count() > 0)

        # Open settings panel
        settings.first.locator("summary").click()
        page.wait_for_timeout(300)

        check("Aspect ratio dropdown",
              page.locator("#cfgAspect").count() > 0)
        check("Quality dropdown",
              page.locator("#cfgQuality").count() > 0)
        check("Style dropdown",
              page.locator("#cfgStyle").count() > 0)
        check("Sub-style dropdown",
              page.locator("#cfgSubStyle").count() > 0)
        check("Clip duration slider",
              page.locator("#cfgClipDur").count() > 0)
        check("Subtitle dropdown",
              page.locator("#cfgSubtitle").count() > 0)

        # Test changing aspect ratio
        page.select_option("#cfgAspect", "9:16")
        page.screenshot(path="/tmp/yt_e2e_02_settings.png", full_page=True)
        check("Aspect ratio changeable",
              page.locator("#cfgAspect").input_value() == "9:16")

        # Test style selection
        page.select_option("#cfgStyle", "vintage")
        check("Style changeable",
              page.locator("#cfgStyle").input_value() == "vintage")

        # Test sub-style selection
        page.select_option("#cfgSubStyle", "hyper_edit")
        check("Sub-style changeable",
              page.locator("#cfgSubStyle").input_value() == "hyper_edit")

        # Test quality selection
        page.select_option("#cfgQuality", "high")
        check("Quality changeable",
              page.locator("#cfgQuality").input_value() == "high")

        # ── 3. Shorts mode ──
        print("\n== 3. Shorts Mode ==")
        page.click("#modeShorts")
        page.wait_for_timeout(300)
        page.screenshot(path="/tmp/yt_e2e_03_shorts.png", full_page=True)

        check("Shorts mode active",
              "active" in (page.locator("#modeShorts").get_attribute("class") or ""))
        check("Shorts header shows",
              page.locator("text=Maak een Short").count() > 0)

        # Check duration options are short (sec instead of min)
        dur_select = page.locator("#durationSelect")
        check("Duration select exists", dur_select.count() > 0)
        dur_options = dur_select.locator("option").all_text_contents()
        check("Duration has sec options",
              any("sec" in o for o in dur_options),
              f"Options: {dur_options}")

        # ── 4. Tools mode ──
        print("\n== 4. Tools Mode ==")
        page.click("#modeTools")
        page.wait_for_timeout(300)
        page.screenshot(path="/tmp/yt_e2e_04_tools.png", full_page=True)

        check("Tools mode active",
              "active" in (page.locator("#modeTools").get_attribute("class") or ""))
        check("Tools header shows",
              page.locator("text=Virale Tools").count() > 0)

        # Check all tool tabs exist
        tabs = page.locator(".tabs .tab")
        tab_texts = tabs.all_text_contents()
        check("Viral Titels tab", "Viral Titels" in tab_texts, f"Tabs: {tab_texts}")
        check("Viral Beschrijvingen tab", "Viral Beschrijvingen" in tab_texts)
        check("Niche Finder tab", "Niche Finder" in tab_texts)
        check("Copyright Check tab", "Copyright Check" in tab_texts)
        check("Shorts uit Video tab", "Shorts uit Video" in tab_texts)
        check("Prompt Templates tab", "Prompt Templates" in tab_texts)

        # ── 5. Viral Title Finder UI ──
        print("\n== 5. Viral Title Finder ==")
        page.locator(".tab", has_text="Viral Titels").click()
        page.wait_for_timeout(300)

        check("Title topic input",
              page.locator("#vtTopic").count() > 0)
        check("Title script textarea",
              page.locator("#vtScript").count() > 0)
        check("Generate button",
              page.locator("text=Genereer 10 titels").count() > 0)

        # ── 6. Niche Finder UI ──
        print("\n== 6. Niche Finder ==")
        page.locator(".tab", has_text="Niche Finder").click()
        page.wait_for_timeout(300)
        page.screenshot(path="/tmp/yt_e2e_06_niche.png", full_page=True)

        check("Niche topic input",
              page.locator("#nicheTopic").count() > 0)
        check("Analyze button",
              page.locator("text=Analyseer niche").count() > 0)

        # ── 7. Copyright Checker UI ──
        print("\n== 7. Copyright Checker ==")
        page.locator(".tab", has_text="Copyright Check").click()
        page.wait_for_timeout(300)

        check("Copyright URL input",
              page.locator("#copyrightUrl").count() > 0)
        check("Check button",
              page.locator("text=Check copyright").count() > 0)

        # ── 8. Highlight Extractor UI ──
        print("\n== 8. Shorts uit Video ==")
        page.locator(".tab", has_text="Shorts uit Video").click()
        page.wait_for_timeout(300)

        check("File upload input",
              page.locator("#hlVideoFile").count() > 0)
        check("Count select",
              page.locator("#hlCount").count() > 0)
        check("Extract button",
              page.locator("text=Zoek highlights").count() > 0)

        # ── 9. Prompt Templates UI ──
        print("\n== 9. Prompt Templates ==")
        page.locator(".tab", has_text="Prompt Templates").click()
        page.wait_for_timeout(1000)
        page.screenshot(path="/tmp/yt_e2e_09_prompts.png", full_page=True)

        check("Template cards loaded",
              page.locator(".result-card").count() > 0)
        check("Script templates section",
              page.locator("text=Script Templates").count() > 0)

        # ── 10. Back to Video mode, check state preserved ──
        print("\n== 10. Mode Switching ==")
        page.click("#modeSingle")
        page.wait_for_timeout(300)

        check("Back to video mode",
              "active" in (page.locator("#modeSingle").get_attribute("class") or ""))
        check("Step 0 renders",
              page.locator("#topicInput").count() > 0)

        # ── 11. Batch mode ──
        print("\n== 11. Batch Mode ==")
        page.click("#modeBatch")
        page.wait_for_timeout(300)
        page.screenshot(path="/tmp/yt_e2e_11_batch.png", full_page=True)

        check("Batch mode active",
              "active" in (page.locator("#modeBatch").get_attribute("class") or ""))
        check("Weekplanner renders",
              page.locator("text=Weekplanner").count() > 0)

        # ── 12. API status endpoint ──
        print("\n== 12. API Checks ==")
        resp = page.request.get("http://localhost:3333/api/status")
        check("API /status returns 200", resp.status == 200)
        data = resp.json()
        check("API returns key statuses", "openai" in data and "elevenlabs" in data)

        resp2 = page.request.get("http://localhost:3333/api/voices")
        check("API /voices returns 200", resp2.status == 200)
        voices = resp2.json()
        check("Voices list populated", len(voices.get("voices", [])) >= 7)

        resp3 = page.request.get("http://localhost:3333/api/prompt-templates")
        check("API /prompt-templates returns 200", resp3.status == 200)
        templates = resp3.json()
        check("Templates populated", len(templates.get("templates", [])) >= 10)

        browser.close()

    # ── Summary ──
    print(f"\n{'='*50}")
    print(f"RESULTS: {len(PASSED)} passed, {len(ERRORS)} failed")
    if ERRORS:
        print(f"\nFailed tests:")
        for e in ERRORS:
            print(f"  - {e}")
    print(f"{'='*50}")

    print(f"\nScreenshots saved to /tmp/yt_e2e_*.png")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
