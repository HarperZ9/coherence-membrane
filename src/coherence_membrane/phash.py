"""Perceptual hashing and drift — the membrane's "has this actually changed?".

Identity (SHA-256) answers *exactly the same bytes?*.  A perceptual hash
answers the softer, sometimes more useful question *visually the same?* — so a
re-encode that is byte-different but pixel-identical reads as a small distance,
while a real visual change reads as a large one.

The drift verdict is a closed lattice, mirroring EMET:
  MATCH        identical bytes (sha256 equal) — the strongest statement.
  DRIFT        bytes differ; the perceptual distance quantifies how much.
  UNVERIFIABLE at least one side could not be perceptually hashed (e.g. an
               unsupported PNG), so visual similarity cannot be confirmed.

Honesty: a dHash is a coarse 64-bit fingerprint, not a semantic understanding
of the image.  It says "the low-frequency structure changed by N bits", not
"the meaning changed".  Callers treat distance as advisory evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from .pngview import DecodedImage

MATCH = "MATCH"
DRIFT = "DRIFT"
UNVERIFIABLE = "UNVERIFIABLE"
DRIFT_VERDICTS = {MATCH, DRIFT, UNVERIFIABLE}

# dHash works on a (HASH_W+1) x HASH_H grayscale grid: HASH_W comparisons per row.
HASH_W = 8
HASH_H = 8


def _to_grayscale(img: DecodedImage) -> list[int]:
    """Project pixels to a single 8-bit luma channel (row-major, len w*h)."""
    px = img.pixels
    ch = img.channels
    n = img.width * img.height
    gray = [0] * n
    if ch == 1:  # grayscale
        for i in range(n):
            gray[i] = px[i]
    elif ch == 2:  # grayscale + alpha
        for i in range(n):
            gray[i] = px[i * 2]
    else:  # 3 (RGB) or 4 (RGBA): Rec.601 luma over the first three channels
        for i in range(n):
            base = i * ch
            r, g, b = px[base], px[base + 1], px[base + 2]
            gray[i] = (r * 299 + g * 587 + b * 114) // 1000
    return gray


def _downscale(gray: list[int], w: int, h: int, tw: int, th: int) -> list[int]:
    """Box-average downscale of a grayscale image to tw x th."""
    out = [0] * (tw * th)
    for ty in range(th):
        y0 = (ty * h) // th
        y1 = max(y0 + 1, ((ty + 1) * h) // th)
        for tx in range(tw):
            x0 = (tx * w) // tw
            x1 = max(x0 + 1, ((tx + 1) * w) // tw)
            total = 0
            count = 0
            for yy in range(y0, y1):
                row = yy * w
                for xx in range(x0, x1):
                    total += gray[row + xx]
                    count += 1
            out[ty * tw + tx] = total // count if count else 0
    return out


def perceptual_hash(img: DecodedImage) -> int:
    """64-bit difference hash (dHash) of a decoded image.

    Downscale to (HASH_W+1) x HASH_H grayscale, then for each row set a bit per
    adjacent-pixel comparison (left brighter than right).
    """
    gray = _to_grayscale(img)
    small = _downscale(gray, img.width, img.height, HASH_W + 1, HASH_H)
    bits = 0
    for y in range(HASH_H):
        row = y * (HASH_W + 1)
        for x in range(HASH_W):
            bits <<= 1
            if small[row + x] > small[row + x + 1]:
                bits |= 1
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


@dataclass(frozen=True)
class DriftVerdict:
    """Result of comparing a current artifact against a baseline.

    verdict   — one of MATCH / DRIFT / UNVERIFIABLE.
    distance  — perceptual Hamming distance (0..64), or None if UNVERIFIABLE.
    reason    — human-readable explanation.
    """

    verdict: str
    distance: int | None
    reason: str


def compare_drift(
    baseline_sha256: str | None,
    current_sha256: str | None,
    baseline_phash: int | None,
    current_phash: int | None,
) -> DriftVerdict:
    """Compare a current artifact against a baseline, fail-closed.

    Exact byte equality is MATCH.  Byte-difference with both perceptual hashes
    present is DRIFT (distance quantifies it).  A missing identity or perceptual
    hash on either side is UNVERIFIABLE — never silently MATCH.
    """
    if not baseline_sha256 or not current_sha256:
        return DriftVerdict(UNVERIFIABLE, None, "a SHA-256 identity is missing on one side")
    if baseline_sha256 == current_sha256:
        return DriftVerdict(MATCH, 0, "identical bytes (sha256 equal)")
    if baseline_phash is None or current_phash is None:
        return DriftVerdict(
            UNVERIFIABLE,
            None,
            "bytes differ but a perceptual hash is missing — visual similarity cannot be confirmed",
        )
    dist = hamming(baseline_phash, current_phash)
    return DriftVerdict(DRIFT, dist, f"bytes differ; perceptual distance {dist}/64")
