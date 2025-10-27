"""
Pure-PIL image utilities for perceptual hashing and similarity.

No numpy or scikit-image dependencies - uses only PIL/Pillow.
Implements aHash and dHash for perceptual similarity detection.
"""

from PIL import Image, ImageOps
import base64
import io
import re
import os
from typing import Union

BytesOrStr = Union[bytes, str]


def load_image(x: BytesOrStr) -> Image.Image:
    """Accept bytes, base64 data URI, or path; return RGB image."""
    if x is None or x == "":
        # blank image (white 64×64)
        return Image.new("RGB", (64, 64), "white")
    if isinstance(x, bytes):
        return Image.open(io.BytesIO(x)).convert("RGB")
    if isinstance(x, str):
        # data URI
        if x.strip().startswith("data:image"):
            b64 = re.sub("^data:image/.+;base64,", "", x)
            return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
        # file path
        if os.path.exists(x):
            return Image.open(x).convert("RGB")
        # treat as base64
        try:
            return Image.open(io.BytesIO(base64.b64decode(x))).convert("RGB")
        except Exception:
            pass
    # fallback: blank
    return Image.new("RGB", (64, 64), "white")


def _to_gray(img: Image.Image) -> Image.Image:
    return ImageOps.grayscale(img)


def _resize(img: Image.Image, size: int = 8) -> Image.Image:
    return img.resize((size, size), Image.LANCZOS)


def ahash(img: Image.Image, size: int = 8) -> int:
    """Average hash."""
    g = _resize(_to_gray(img), size)
    px = list(g.getdata())
    avg = sum(px) / len(px)
    bits = "".join("1" if p > avg else "0" for p in px)
    return int(bits, 2)


def dhash(img: Image.Image, size: int = 8) -> int:
    """Difference hash."""
    g = _resize(_to_gray(img), size + 1)
    pixels = list(g.getdata())
    w, h = g.size
    bits = []
    for y in range(h):
        row = pixels[y * w:(y + 1) * w]
        for x in range(w - 1):
            bits.append("1" if row[x] > row[x + 1] else "0")
    return int("".join(bits), 2)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def perceptual_similarity(prev_img: Image.Image, cur_img: Image.Image) -> float:
    """Return similarity 0..1 combining aHash+dHash."""
    ah1, ah2 = ahash(prev_img), ahash(cur_img)
    dh1, dh2 = dhash(prev_img), dhash(cur_img)
    max_bits = 64
    ah_diff = hamming(ah1, ah2) / max_bits
    dh_diff = hamming(dh1, dh2) / max_bits
    sim = 1 - ((ah_diff + dh_diff) / 2)
    return round(max(0.0, min(1.0, sim)), 4)
