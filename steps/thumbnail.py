"""Generate YouTube thumbnail using Gemini image generation + Pillow."""
import io
from pathlib import Path
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont
from config import GEMINI_API_KEY, OUTPUT_DIR
from steps.pipeline_config import PipelineConfig
from steps.style_registry import get_style

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_thumbnail(topic: str, title: str, output_name: str = "thumbnail", *, config=None) -> Path:
    """Generate a YouTube thumbnail with Gemini image generation + text overlay."""
    if config is None:
        config = PipelineConfig()

    style_data = get_style(config.style)
    thumb_style = style_data.get("thumbnail_style", "dramatic, cinematic")

    prompt = (
        f"Generate a YouTube thumbnail background image for a video about {topic}. "
        f"Style: {thumb_style}. "
        "High contrast, vibrant colors, no text in the image. 16:9 aspect ratio. "
        "Cinematic lighting, eye-catching, professional quality."
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
        ),
    )

    # Extract generated image
    output_path = OUTPUT_DIR / f"{output_name}.png"
    img = None

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            img = Image.open(io.BytesIO(part.inline_data.data))
            break

    if img is None:
        raise RuntimeError("Gemini returned no image in response")

    # Resize to YouTube thumbnail dimensions
    img = img.resize((1280, 720), Image.LANCZOS)

    # Add text overlay
    draw = ImageDraw.Draw(img)

    font = None
    for font_path in [
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFCompact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        try:
            font = ImageFont.truetype(font_path, 80)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    text = title.upper()[:40]
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (1280 - text_width) // 2
    y = 560

    # Shadow
    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, -3), (0, 3), (-3, 0), (3, 0)]:
        draw.text((x + dx, y + dy), text, fill="black", font=font)
    # Main text
    draw.text((x, y), text, fill="white", font=font)

    img.save(str(output_path), quality=95)
    return output_path


def generate_thumbnail_nanobanana(
    prompt: str,
    name: str,
    base_image_path: Path | None = None,
) -> Path:
    """Generate or edit a thumbnail using Gemini image generation."""
    contents: list = []

    if base_image_path and base_image_path.exists():
        img_bytes = base_image_path.read_bytes()
        mime = "image/png" if base_image_path.suffix == ".png" else "image/jpeg"
        contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))

    full_prompt = (
        f"{prompt}. "
        "Make it a YouTube thumbnail style: dramatic, high contrast, 16:9 aspect ratio, "
        "eye-catching colors, cinematic lighting."
    )
    contents.append(full_prompt)

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
        ),
    )

    output_path = OUTPUT_DIR / f"{name}.png"

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            img = Image.open(io.BytesIO(part.inline_data.data))
            img = img.resize((1280, 720), Image.LANCZOS)
            img.save(str(output_path), quality=95)
            return output_path

    raise RuntimeError("Gemini returned no image in response")


def apply_thumbnail_edits(base_path: Path, edits: dict) -> Path:
    """Apply edits (crop, text overlays, filters) to a thumbnail image."""
    from PIL import ImageEnhance

    img = Image.open(base_path).convert("RGB")

    crop = edits.get("crop")
    if crop:
        x, y, w, h = crop["x"], crop["y"], crop["width"], crop["height"]
        img = img.crop((x, y, x + w, y + h))
        img = img.resize((1280, 720), Image.LANCZOS)

    filters = edits.get("filters", {})
    if "brightness" in filters:
        img = ImageEnhance.Brightness(img).enhance(filters["brightness"])
    if "contrast" in filters:
        img = ImageEnhance.Contrast(img).enhance(filters["contrast"])
    if "saturation" in filters:
        img = ImageEnhance.Color(img).enhance(filters["saturation"])

    for overlay in edits.get("text_overlays", []):
        draw = ImageDraw.Draw(img)
        font_size = overlay.get("font_size", 60)
        color = overlay.get("color", "#FFFFFF")

        font = None
        for font_path in [
            "/System/Library/Fonts/Supplemental/Impact.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFCompact.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]:
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except OSError:
                continue
        if font is None:
            font = ImageFont.load_default()

        text = overlay.get("text", "")
        x = overlay.get("x", 0)
        y = overlay.get("y", 0)

        for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
            draw.text((x + dx, y + dy), text, fill="black", font=font)
        draw.text((x, y), text, fill=color, font=font)

    output_path = OUTPUT_DIR / f"{base_path.stem}_edited.png"
    img.save(str(output_path), quality=95)
    return output_path
