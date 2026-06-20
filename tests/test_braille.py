from __future__ import annotations

from coherence_membrane.field import Field, FieldKind
from coherence_membrane.braille import pack_braille, braille_text, braille_view


def _occ(w, h, vals, unknown=None):
    if unknown is None:
        unknown = (False,) * (w * h)
    return Field(w, h, FieldKind.OCCUPANCY, tuple(float(v) for v in vals), tuple(unknown))


def test_pack_full_cell_is_solid_glyph():
    assert pack_braille(_occ(2, 4, [1] * 8)) == ["⣿"]


def test_pack_empty_cell_is_blank_glyph():
    assert pack_braille(_occ(2, 4, [0] * 8)) == ["⠀"]


def test_pack_single_top_left_dot():
    vals = [0] * 8
    vals[0] = 1  # cell (x=0, y=0) -> dot 1 -> 0x01
    assert pack_braille(_occ(2, 4, vals)) == ["⠁"]


def test_pack_unknown_cell_is_not_ink():
    vals = [1] * 8
    unk = [False] * 8
    unk[0] = True  # (0,0) unknown -> no dot even though value is 1
    assert pack_braille(_occ(2, 4, vals, unknown=unk)) == [chr(0x2800 + 0xFE)]


def test_braille_text_joins_rows():
    assert braille_text(["ab", "cd"]) == "ab\ncd"


def test_braille_view_downscales_to_one_solid_glyph():
    f = _occ(4, 8, [1] * 32)  # 4x8 solid -> 1 glyph (2x4 dots), all set
    assert braille_view(f, cols=1, rows=1) == ["⣿"]


def test_braille_view_default_rows_preserve_aspect():
    f = _occ(8, 8, [1] * 64)
    view = braille_view(f, cols=2)   # dot_w=4 -> dot_h~4 -> 1 glyph row
    assert len(view) == 1 and len(view[0]) == 2
