"""Tests for thumbnail.py with style integration."""

from unittest.mock import patch, MagicMock

import pytest

from steps.pipeline_config import PipelineConfig


class TestGenerateThumbnailStyle:
    """Test that generate_thumbnail uses style for DALL-E prompt."""

    @patch("steps.thumbnail.urllib.request.urlopen")
    @patch("steps.thumbnail.OpenAI")
    def test_vintage_style_in_dalle_prompt(self, mock_cls, mock_urlopen):
        from steps.thumbnail import generate_thumbnail

        client = MagicMock()
        mock_cls.return_value = client
        # Mock DALL-E response
        img_data = MagicMock()
        img_data.url = "https://example.com/fake.png"
        response = MagicMock()
        response.data = [img_data]
        client.images.generate.return_value = response

        # Mock URL download - return minimal PNG
        import struct, zlib
        def make_minimal_png():
            # 1x1 red pixel PNG
            raw = b'\x00\xff\x00\x00'
            compressed = zlib.compress(raw)
            def chunk(ctype, data):
                c = ctype + data
                return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
            return (b'\x89PNG\r\n\x1a\n' +
                    chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) +
                    chunk(b'IDAT', compressed) +
                    chunk(b'IEND', b''))

        mock_resp = MagicMock()
        mock_resp.read.return_value = make_minimal_png()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        cfg = PipelineConfig(style="vintage")
        try:
            generate_thumbnail("test", "Test Title", "test_thumb", config=cfg)
        except Exception:
            pass  # PIL might fail on minimal PNG, that's OK

        # Verify the DALL-E prompt contains vintage style
        call_args = client.images.generate.call_args
        prompt = call_args[1]["prompt"]
        assert "vintage" in prompt.lower() or "aged" in prompt.lower()

    @patch("steps.thumbnail.urllib.request.urlopen")
    @patch("steps.thumbnail.OpenAI")
    def test_80s_style_in_dalle_prompt(self, mock_cls, mock_urlopen):
        from steps.thumbnail import generate_thumbnail

        client = MagicMock()
        mock_cls.return_value = client
        img_data = MagicMock()
        img_data.url = "https://example.com/fake.png"
        response = MagicMock()
        response.data = [img_data]
        client.images.generate.return_value = response

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'\x89PNG' + b'\x00' * 100  # will fail but that's fine
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        cfg = PipelineConfig(style="80s")
        try:
            generate_thumbnail("test", "Test Title", "test_thumb", config=cfg)
        except Exception:
            pass

        call_args = client.images.generate.call_args
        prompt = call_args[1]["prompt"]
        assert "neon" in prompt.lower() or "retro" in prompt.lower() or "80s" in prompt.lower()

    @patch("steps.thumbnail.urllib.request.urlopen")
    @patch("steps.thumbnail.OpenAI")
    def test_no_config_backward_compatible(self, mock_cls, mock_urlopen):
        from steps.thumbnail import generate_thumbnail

        client = MagicMock()
        mock_cls.return_value = client
        img_data = MagicMock()
        img_data.url = "https://example.com/fake.png"
        response = MagicMock()
        response.data = [img_data]
        client.images.generate.return_value = response

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'\x89PNG' + b'\x00' * 100
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        try:
            generate_thumbnail("test", "Test Title", "test_thumb")
        except Exception:
            pass

        # Should still call DALL-E with some prompt
        assert client.images.generate.called
        prompt = client.images.generate.call_args[1]["prompt"]
        assert "thumbnail" in prompt.lower()


class TestApplyThumbnailEdits:
    def test_add_text_overlay(self, tmp_path):
        from steps.thumbnail import apply_thumbnail_edits
        from PIL import Image

        # Create a test image
        img = Image.new("RGB", (1280, 720), color="blue")
        base_path = tmp_path / "base.png"
        img.save(str(base_path))

        edits = {
            "text_overlays": [
                {"text": "HELLO", "x": 100, "y": 100, "font_size": 60, "color": "#FFFFFF"}
            ],
        }

        result = apply_thumbnail_edits(base_path, edits)
        assert result.exists()
        result_img = Image.open(result)
        assert result_img.size == (1280, 720)

    def test_apply_brightness_filter(self, tmp_path):
        from steps.thumbnail import apply_thumbnail_edits
        from PIL import Image

        img = Image.new("RGB", (1280, 720), color=(128, 128, 128))
        base_path = tmp_path / "base.png"
        img.save(str(base_path))

        edits = {
            "filters": {"brightness": 1.5},
        }

        result = apply_thumbnail_edits(base_path, edits)
        assert result.exists()

    def test_apply_crop(self, tmp_path):
        from steps.thumbnail import apply_thumbnail_edits
        from PIL import Image

        img = Image.new("RGB", (1280, 720), color="red")
        base_path = tmp_path / "base.png"
        img.save(str(base_path))

        edits = {
            "crop": {"x": 100, "y": 50, "width": 800, "height": 450},
        }

        result = apply_thumbnail_edits(base_path, edits)
        assert result.exists()
        # Should be resized back to 1280x720 after crop
        result_img = Image.open(result)
        assert result_img.size == (1280, 720)
