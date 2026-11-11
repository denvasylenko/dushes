"""Phone photos are shrunk before they reach the model (its per-image limit is about 7.5 MB of bytes)."""
from __future__ import annotations

import base64
import io
import os

from PIL import Image

from formguide.models import IMAGE_MAX_BYTES, IMAGE_MAX_SIDE, file_block, fit_image


def png(w: int, h: int, mode: str = "RGB") -> bytes:
    im = Image.frombytes(mode, (w, h), os.urandom(w * h * len(mode)))   # noise does not compress: a big file
    out = io.BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


def test_a_big_photo_is_shrunk_to_a_jpeg():
    big = png(4032, 3024)
    assert len(big) > 10 * 1024 * 1024
    data, mt = fit_image(big, "image/png")
    assert mt == "image/jpeg" and len(data) <= IMAGE_MAX_BYTES
    assert max(Image.open(io.BytesIO(data)).size) == IMAGE_MAX_SIDE
    block = file_block("IMG_3711.png", "image/png", big)
    assert block["mime_type"] == "image/jpeg" and len(base64.b64decode(block["base64"])) == len(data)


def test_small_images_and_transparency_are_kept():
    small = png(300, 200)
    assert fit_image(small, "image/png") == (small, "image/png")
    data, mt = fit_image(png(2600, 2600, "RGBA"), "image/png")
    assert mt == "image/png" and max(Image.open(io.BytesIO(data)).size) == IMAGE_MAX_SIDE
