"""Generate YouTube thumbnail using DALL-E + Pillow or Gemini image generation."""
import base64
import io
import ssl
import urllib.request
from pathlib import Path
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from config import OPENAI_API_KEY, GEMINI_API_KEY, OUTPUT_DIR
from steps.pipeline_config import PipelineConfig
from steps.style_registry import get_style


def generate_thumbnail(topic: str, title: str, output_name: str = "thumbnail", *, config=None) -> Path:
    """Generate a YouTube thumbnail with AI image + text overlay."""
    if config is None:
        config = PipelineConfig()

    client = OpenAI(api_key=OPENAI_API_KEY)

    # Get style-specific thumbnail instructions
    style_data = get_style(config.style)
    thumb_style = style_data.get("thumbnail_style", "dramatic, cinematic")

    prompt = (
        f"YouTube thumbnail background for a video about {topic}. "
        f"{thumb_style}. "
        "High contrast, no text in the image. 16:9 aspect ratio."
    )

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1792x1024",
        quality="hd",
        n=1,
    )

    image_url = response.data[0].url
    temp_path = OUTPUT_DIR / "thumb_base.png"

    # Download with SSL workaround
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(image_url)
    with urllib.request.urlopen(req, context=ctx) as resp:
        temp_path.write_bytes(resp.read())

    # Add text overlay
    img = Image.open(temp_path).resize((1280, 720))
    draw = ImageDraw.Draw(img)

    # Try bold fonts
    font = None
    for font_path in [
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFCompact.ttf",
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
    for dx, dy in [(-2,-2),(2,-2),(-2,2),(2,2),(0,-3),(0,3),(-3,0),(3,0)]:
        draw.text((x + dx, y + dy), text, fill="black", font=font)
    # Main text
    draw.text((x, y), text, fill="white", font=font)

    output_path = OUTPUT_DIR / f"{output_name}.png"
    img.save(str(output_path), quality=95)
    temp_path.unlink(missing_ok=True)

    return output_path


def generate_thumbnail_nanobanana(
    prompt: str,
    name: str,
    base_image_path: Path | None = None,
) -> Path:
    """Generate or edit a thumbnail using Gemini image generation (Nano Banana)."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    contents: list = []

    # If a base image is provided, include it for editing
    if base_image_path and base_image_path.exists():
        img_bytes = base_image_path.read_bytes()
        mime = "image/png" if base_image_path.suffix == ".png" else "image/jpeg"
        contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))

    # Add the text prompt
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

    # Extract generated image from response parts
    output_path = OUTPUT_DIR / f"{name}.png"

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            img_data = part.inline_data.data
            img = Image.open(io.BytesIO(img_data))
            # Resize to standard YouTube thumbnail dimensions
            img = img.resize((1280, 720), Image.LANCZOS)
            img.save(str(output_path), quality=95)
            return output_path

    raise RuntimeError("Gemini returned no image in response")


def apply_thumbnail_edits(base_path: Path, edits: dict) -> Path:
    """Apply edits (crop, text overlays, filters) to a thumbnail image.

    Args:
        base_path: Path to the base image.
        edits: Dict with optional keys:
            - crop: {x, y, width, height}
            - text_overlays: [{text, x, y, font_size, color}]
            - filters: {brightness, contrast, saturation}
    """
    from PIL import ImageEnhance

    img = Image.open(base_path).convert("RGB")

    # Apply crop
    crop = edits.get("crop")
    if crop:
        x, y, w, h = crop["x"], crop["y"], crop["width"], crop["height"]
        img = img.crop((x, y, x + w, y + h))
        img = img.resize((1280, 720), Image.LANCZOS)

    # Apply filters
    filters = edits.get("filters", {})
    if "brightness" in filters:
        img = ImageEnhance.Brightness(img).enhance(filters["brightness"])
    if "contrast" in filters:
        img = ImageEnhance.Contrast(img).enhance(filters["contrast"])
    if "saturation" in filters:
        img = ImageEnhance.Color(img).enhance(filters["saturation"])

    # Apply text overlays
    for overlay in edits.get("text_overlays", []):
        draw = ImageDraw.Draw(img)
        font_size = overlay.get("font_size", 60)
        color = overlay.get("color", "#FFFFFF")

        font = None
        for font_path in [
            "/System/Library/Fonts/Supplemental/Impact.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFCompact.ttf",
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

        # Shadow
        for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
            draw.text((x + dx, y + dy), text, fill="black", font=font)
        draw.text((x, y), text, fill=color, font=font)

    output_path = OUTPUT_DIR / f"{base_path.stem}_edited.png"
    img.save(str(output_path), quality=95)
    return output_path
