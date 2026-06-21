from __future__ import annotations

from coherence_membrane.field import Field, FieldKind
from coherence_membrane.livestate import field_canonical_bytes, field_state_sha, FieldSnapshot


def _f(values, unknown, w=2, h=2, kind=FieldKind.LUMINANCE):
    return Field(w, h, kind, tuple(values), tuple(unknown))


def test_state_sha_full_width_and_deterministic():
    f = _f([0.1, 0.2, 0.3, 0.4], [False] * 4)
    assert len(field_state_sha(f)) == 64
    assert field_state_sha(f) == field_state_sha(f)


def test_unknown_cells_zeroed_in_identity():
    # equal in KNOWN cells, identical unknown masks, differ only UNDER the mask
    a = _f([0.5, 9.9, 0.3, 0.4], [False, True, False, False])
    b = _f([0.5, 0.0, 0.3, 0.4], [False, True, False, False])
    assert field_state_sha(a) == field_state_sha(b)


def test_known_value_change_changes_identity():
    a = _f([0.5, 0.2, 0.3, 0.4], [False] * 4)
    b = _f([0.6, 0.2, 0.3, 0.4], [False] * 4)
    assert field_state_sha(a) != field_state_sha(b)


def test_unknown_mask_change_changes_identity():
    a = _f([0.5, 0.2, 0.3, 0.4], [False] * 4)
    b = _f([0.5, 0.2, 0.3, 0.4], [True, False, False, False])
    assert field_state_sha(a) != field_state_sha(b)


def test_snapshot_holds_sha_and_tick():
    f = _f([0.1, 0.2, 0.3, 0.4], [False] * 4)
    s = FieldSnapshot(f, field_state_sha(f), 0)
    assert s.tick == 0 and s.state_sha == field_state_sha(f) and s.verdict == "MATCH"
