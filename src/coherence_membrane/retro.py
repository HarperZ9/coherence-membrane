"""Vintage CGI render pipeline — pure functions, stdlib only, deterministic.

render_vintage composes a 7-step pipeline:
  1. REUSE  color_field_from_png -> ColorField (OKLab)
  2. NEW    downscale_color_field -> smaller ColorField (box-average)
  3. REUSE  quantize / palettes.get_palette -> palette (OKLab triples)
  4. NEW    ordered_dither (Bayer) -> palette indices per pixel
  5. REUSE  field_ops.distance (SDF modulation, optional)
  6. NEW    nearest-neighbor upscale + scanlines (CRT effect)
  7. REUSE  encode_png -> output PNG bytes

Cardinal property: identical (source_png, params) -> identical output bytes
and identical output_sha256.  Guaranteed by:
  - All sub-functions are pure and deterministic (verified by their own tests).
  - No random number generators, timestamps, or external state in the pipeline.
  - sRGB clamping is deterministic (min/max on fixed inputs).
  - Bayer thresholds are computed from a fixed recurrence (no seed).
"""
from __future__ import annotations

from dataclasses import dataclass

from .color import oklab_to_srgb, Triple, srgb_to_oklab, srgb_to_linear
from .color_field import ColorField, color_field_from_png, downscale_color_field
from .color_quantize import quantize, palette_to_hex
from .dither import ordered_dither
from .field import Field, FieldKind
from .field_ops import distance, threshold
from .lowering import field_from_png
from .observation import sha256_hex
from .palettes import get_palette
from .pngencode import encode_png
from .pngview import decode_png

# Upscale factor for the nearest-neighbor upsample in step 6.
# Output width = target_width * UPSCALE_FACTOR.
UPSCALE_FACTOR: int = 4


@dataclass(frozen=True)
class RenderResult:
    """Result of render_vintage: output PNG bytes and full provenance."""

    output_png: bytes
    source_sha256: str
    params: dict
    output_sha256: str
    palette_hex: list[str]


# ---------------------------------------------------------------------------
# Internal helpers — pure, deterministic
# ---------------------------------------------------------------------------

def _palette_from_rgb(
    rgb_palette: list[tuple[int, int, int]],
) -> tuple[Triple, ...]:
    """Convert a list of (R, G, B) int tuples to OKLab triples."""
    return tuple(srgb_to_oklab((r / 255.0, g / 255.0, b / 255.0)) for r, g, b in rgb_palette)


def _palette_indices_to_lab(
    indices: tuple[int, ...],
    palette: tuple[Triple, ...],
    width: int,
    height: int,
) -> list[Triple]:
    """Map palette indices back to OKLab triples, row-major."""
    result: list[Triple] = []
    for i in range(height):
        for j in range(width):
            idx = indices[i * width + j]
            if idx < 0:
                result.append((0.0, 0.0, 0.0))
            else:
                result.append(palette[idx])
    return result


def _nearest_neighbor_upscale(
    pixels_rgb: list[tuple[int, int, int]],
    src_w: int,
    src_h: int,
    scale: int,
) -> list[tuple[int, int, int]]:
    """Nearest-neighbor upscale by integer scale factor. Deterministic."""
    dst_w = src_w * scale
    dst_h = src_h * scale
    out: list[tuple[int, int, int]] = [None] * (dst_w * dst_h)  # type: ignore[list-item]
    for dy in range(dst_h):
        sy = dy // scale
        for dx in range(dst_w):
            sx = dx // scale
            out[dy * dst_w + dx] = pixels_rgb[sy * src_w + sx]
    return out


def _apply_scanlines(
    pixels_rgb: list[tuple[int, int, int]],
    width: int,
    height: int,
) -> list[tuple[int, int, int]]:
    """CRT scanline effect: darken alternate rows + a slight bloom on bright rows.

    - Even rows (0-indexed): darken to 65% of original (scanline gap).
    - Odd rows: apply subtle bloom (brighten by 10%, clamped to 255).
    Deterministic; no external state.
    """
    out: list[tuple[int, int, int]] = []
    for y in range(height):
        for x in range(width):
            r, g, b = pixels_rgb[y * width + x]
            if y % 2 == 0:
                # Scanline gap: darken
                r = int(r * 65 // 100)
                g = int(g * 65 // 100)
                b = int(b * 65 // 100)
            else:
                # Slight bloom: brighten
                r = min(255, int(r * 110 // 100))
                g = min(255, int(g * 110 // 100))
                b = min(255, int(b * 110 // 100))
            out.append((r, g, b))
    return out


def _lab_to_luminance(lab: Triple) -> float:
    """OKLab L channel as approximate luminance (0=black, 1=white)."""
    return lab[0]  # L channel is perceptual lightness


def _build_luminance_field_from_color_field(field: ColorField) -> Field:
    """Derive a LUMINANCE Field from a ColorField via OKLab L channel."""
    values = tuple(_lab_to_luminance(lab) for lab in field.lab)
    return Field(field.width, field.height, FieldKind.LUMINANCE, values, field.unknown)


def _apply_sdf_shade(
    lab_pixels: list[Triple],
    sdf_field: Field,
    src_w: int,
    src_h: int,
) -> list[Triple]:
    """Modulate brightness by SDF for a vintage early-3D look.

    Cells further inside (large negative SDF) are darker (shadow).
    Cells near the surface (SDF ≈ 0) keep original brightness.
    Cells outside (positive SDF) get a slight brightening.
    Modulation is clamped and deterministic.

    The SDF is normalized to a [-1, 1] range before applying so the effect
    is scale-independent.  Unknown SDF cells are left unmodified.
    """
    # Compute SDF range for normalization
    known_vals = [sdf_field.values[i] for i in range(len(sdf_field.values))
                  if not sdf_field.unknown[i]]
    if not known_vals:
        return lab_pixels

    sdf_min = min(known_vals)
    sdf_max = max(known_vals)
    sdf_range = sdf_max - sdf_min if sdf_max != sdf_min else 1.0

    result: list[Triple] = []
    for i, lab in enumerate(lab_pixels):
        if sdf_field.unknown[i]:
            result.append(lab)
            continue
        # Normalize SDF to [-1, 1]
        sdf_norm = 2.0 * (sdf_field.values[i] - sdf_min) / sdf_range - 1.0
        # Modulation: inside (negative) darkens, outside (positive) brightens
        # Factor in [0.5, 1.3] range
        factor = 1.0 + 0.3 * sdf_norm
        factor = max(0.5, min(1.3, factor))
        L, a, b = lab
        L_mod = max(0.0, min(1.0, L * factor))
        result.append((L_mod, a, b))

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_vintage(
    source_png: bytes,
    *,
    target_width: int,
    palette_k: int = 8,
    palette: str | None = None,
    dither: bool = True,
    scanlines: bool = True,
    sdf_shade: bool = False,
) -> RenderResult:
    """Render a source PNG through a vintage CGI pipeline.

    Pipeline (step labels match the brief):
      1. REUSE  color_field_from_png(source_png) -> ColorField
      2. NEW    downscale_color_field(field, target_width) -> smaller ColorField
      3. REUSE  quantize(field, palette_k) OR palettes.get_palette(palette)
                -> OKLab palette triples
      4. NEW    ordered_dither (Bayer) mapping -> palette index per pixel
               (or nearest-only if dither=False)
      5. REUSE  field_ops.distance (SDF) -> modulate brightness for 3D shading
               (only if sdf_shade=True)
      6. NEW    nearest-neighbor upscale by UPSCALE_FACTOR + scanline/CRT effect
               (scanlines only if scanlines=True)
      7. REUSE  encode_png(...) -> output PNG bytes

    Args:
        source_png:   Raw bytes of an 8-bit RGB/RGBA/grayscale PNG.
        target_width: Width of the quantized low-res image (before upscale).
                      Output width = target_width * UPSCALE_FACTOR.
        palette_k:    Number of colors for median-cut quantization (used when
                      `palette` is None).
        palette:      Name of a fixed retro palette (e.g. 'cga', 'ega').
                      Overrides palette_k when provided.
        dither:       If True, apply Bayer ordered dithering during palette
                      mapping.  If False, use nearest-only (no dither).
        scanlines:    If True, apply CRT scanline effect in step 6.
        sdf_shade:    If True, compute an SDF from the luminance field and
                      modulate per-pixel brightness for an early-3D look.

    Returns:
        RenderResult with output_png bytes, source/output sha256 digests,
        the params dict, and palette_hex list.

    Cardinal property (determinism): identical (source_png, params) always
    yields identical output_png bytes and identical output_sha256.
    """
    # Provenance anchor for the source
    source_sha256 = sha256_hex(source_png)

    # ------------------------------------------------------------------
    # Step 1 (REUSE): Decode source PNG into OKLab ColorField
    # ------------------------------------------------------------------
    color_field = color_field_from_png(source_png)

    # ------------------------------------------------------------------
    # Step 2 (NEW): Box-downscale ColorField to target_width
    # ------------------------------------------------------------------
    small_field = downscale_color_field(color_field, target_width)
    small_w, small_h = small_field.width, small_field.height

    # ------------------------------------------------------------------
    # Step 3 (REUSE / NEW): Build OKLab palette
    # ------------------------------------------------------------------
    if palette is not None:
        # Named retro palette: convert RGB -> OKLab
        rgb_palette = get_palette(palette)
        oklab_palette: tuple[Triple, ...] = _palette_from_rgb(rgb_palette)
        # Build indices by nearest-color mapping (or dither below)
        # We still need an indices tuple for step 4 — compute it here as nearest
        from .color_quantize import _nearest as _cn
        raw_indices = tuple(
            -1 if small_field.unknown[i] else _cn(lab, oklab_palette)
            for i, lab in enumerate(small_field.lab)
        )
    else:
        raw_indices, oklab_palette = quantize(small_field, palette_k)

    # ------------------------------------------------------------------
    # Step 4 (NEW): Ordered Bayer dither (or nearest-only if dither=False)
    # ------------------------------------------------------------------
    if dither:
        palette_indices = ordered_dither(small_field, oklab_palette, bayer_size=4)
    else:
        # Use raw nearest-neighbor mapping directly
        palette_indices = tuple(max(0, i) for i in raw_indices)

    # ------------------------------------------------------------------
    # Step 5 (REUSE): SDF shading (optional)
    # ------------------------------------------------------------------
    # Map indices to OKLab pixel list
    lab_pixels: list[Triple] = _palette_indices_to_lab(
        palette_indices, oklab_palette, small_w, small_h
    )

    if sdf_shade:
        # Derive luminance Field from the small ColorField
        lum_field = _build_luminance_field_from_color_field(small_field)
        # Threshold to OCCUPANCY (pixels brighter than mid-gray = inside)
        from .field_ops import threshold as _thr
        occ_field = _thr(lum_field, 0.5)
        # Compute SDF
        sdf_field = distance(occ_field)
        # Modulate brightness
        lab_pixels = _apply_sdf_shade(lab_pixels, sdf_field, small_w, small_h)

    # ------------------------------------------------------------------
    # Convert OKLab pixels -> 8-bit sRGB
    # ------------------------------------------------------------------
    rgb_pixels: list[tuple[int, int, int]] = []
    for lab in lab_pixels:
        r_f, g_f, b_f = oklab_to_srgb(lab)
        rgb_pixels.append((
            max(0, min(255, round(r_f * 255))),
            max(0, min(255, round(g_f * 255))),
            max(0, min(255, round(b_f * 255))),
        ))

    # ------------------------------------------------------------------
    # Step 6 (NEW): Nearest-neighbor upscale + CRT scanlines
    # ------------------------------------------------------------------
    upscaled = _nearest_neighbor_upscale(rgb_pixels, small_w, small_h, UPSCALE_FACTOR)
    dst_w = small_w * UPSCALE_FACTOR
    dst_h = small_h * UPSCALE_FACTOR

    if scanlines:
        upscaled = _apply_scanlines(upscaled, dst_w, dst_h)

    # Flatten to bytes
    pixel_bytes = bytearray()
    for r, g, b in upscaled:
        pixel_bytes.extend([r, g, b])

    # ------------------------------------------------------------------
    # Step 7 (REUSE): Encode to PNG bytes
    # ------------------------------------------------------------------
    output_png = encode_png(dst_w, dst_h, bytes(pixel_bytes), channels=3)

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------
    output_sha256 = sha256_hex(output_png)

    # Build palette_hex from the OKLab palette (reuse palette_to_hex)
    hex_colors = list(palette_to_hex(oklab_palette))

    # Build params dict
    params: dict = {
        "target_width": target_width,
        "palette_k": palette_k,
        "palette": palette,
        "dither": dither,
        "scanlines": scanlines,
        "sdf_shade": sdf_shade,
    }
    if palette is not None:
        params["palette"] = palette

    return RenderResult(
        output_png=output_png,
        source_sha256=source_sha256,
        params=params,
        output_sha256=output_sha256,
        palette_hex=hex_colors,
    )
