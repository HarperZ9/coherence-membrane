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


from coherence_membrane.livestate import field_diff, field_apply


def test_diff_sparsity_one_cell():
    a = _f([0.1, 0.2, 0.3, 0.4], [False] * 4)
    b = _f([0.1, 0.9, 0.3, 0.4], [False] * 4)
    changes, verdict = field_diff(a, b)
    assert changes == [(1, 0.9, False)] and verdict == "DRIFT"


def test_diff_no_change_is_match():
    a = _f([0.1, 0.2, 0.3, 0.4], [False] * 4)
    changes, verdict = field_diff(a, a)
    assert changes == [] and verdict == "MATCH"


def test_diff_known_to_unknown_is_unverifiable():
    a = _f([0.1, 0.2, 0.3, 0.4], [False] * 4)
    b = _f([0.1, 0.2, 0.3, 0.4], [False, True, False, False])
    changes, verdict = field_diff(a, b)
    assert changes == [(1, 0.0, True)] and verdict == "UNVERIFIABLE"


def test_diff_drift_dominates_unverifiable():
    # one cell changes value (DRIFT) + one cell becomes unknown (UNVERIFIABLE)
    a = _f([0.1, 0.2, 0.3, 0.4], [False] * 4)
    b = _f([0.9, 0.2, 0.3, 0.4], [False, True, False, False])
    _changes, verdict = field_diff(a, b)
    assert verdict == "DRIFT"  # DRIFT is the absorbing bottom of DRIFT_LATTICE


def test_diff_both_unknown_is_no_change():
    a = _f([0.1, 5.0, 0.3, 0.4], [False, True, False, False])
    b = _f([0.1, 9.0, 0.3, 0.4], [False, True, False, False])  # value under mask differs
    changes, verdict = field_diff(a, b)
    assert changes == [] and verdict == "MATCH"


def test_apply_roundtrips_to_new_state():
    a = _f([0.1, 0.2, 0.3, 0.4], [False] * 4)
    b = _f([0.1, 0.9, 0.3, 0.4], [False, True, False, False])
    changes, _ = field_diff(a, b)
    rebuilt = field_apply(a, changes)
    assert field_state_sha(rebuilt) == field_state_sha(b)


from coherence_membrane.livestate import DiffChain, FieldDiff


def test_from_base_and_current():
    f = _f([0.1, 0.2, 0.3, 0.4], [False] * 4)
    c = DiffChain.from_base(f, subject="s")
    assert c.tick == 0
    assert c.current().state_sha == field_state_sha(f)


def test_append_returns_witnessed_diff():
    a = _f([0.1, 0.2, 0.3, 0.4], [False] * 4)
    b = _f([0.1, 0.9, 0.3, 0.4], [False] * 4)
    c = DiffChain.from_base(a, subject="s")
    d = c.append(b)
    assert isinstance(d, FieldDiff)
    assert d.parent_sha == field_state_sha(a)
    assert d.result_sha == field_state_sha(b)
    assert d.verdict == "DRIFT" and d.tick == 1
    assert c.current().state_sha == field_state_sha(b) and c.tick == 1


def test_auto_keyframe_on_interval():
    a = _f([0.0, 0.0, 0.0, 0.0], [False] * 4)
    c = DiffChain.from_base(a, subject="s", checkpoint_interval=2)
    c.append(_f([0.1, 0.0, 0.0, 0.0], [False] * 4))  # tick 1 -> diff
    c.append(_f([0.2, 0.0, 0.0, 0.0], [False] * 4))  # tick 2 -> keyframe (interval)
    from coherence_membrane.livestate import FieldSnapshot
    assert isinstance(c.entries[1], FieldDiff)
    assert isinstance(c.entries[2], FieldSnapshot)


def test_explicit_checkpoint():
    a = _f([0.0, 0.0, 0.0, 0.0], [False] * 4)
    c = DiffChain.from_base(a, subject="s", checkpoint_interval=1000)
    c.append(_f([0.1, 0.0, 0.0, 0.0], [False] * 4))
    snap = c.checkpoint()
    from coherence_membrane.livestate import FieldSnapshot
    assert isinstance(c.entries[c.tick], FieldSnapshot) and snap.tick == c.tick


def test_reconstruct_every_tick_bit_identical():
    states = [_f([float(t) / 10, 0.0, 0.0, 0.0], [False] * 4) for t in range(6)]
    c = DiffChain.from_base(states[0], subject="s", checkpoint_interval=2)  # keyframes at 2,4
    for s in states[1:]:
        c.append(s)
    for t in range(6):
        r = c.reconstruct(t)
        assert r.verdict == "MATCH"
        assert r.state_sha == field_state_sha(states[t]), f"tick {t}"


def test_reconstruct_out_of_range_unverifiable():
    c = DiffChain.from_base(_f([0.0] * 4, [False] * 4), subject="s")
    assert c.reconstruct(5).verdict == "UNVERIFIABLE"


import dataclasses
from coherence_membrane.livestate import ChainVerdict


def _chain():
    states = [_f([float(t) / 10, 0.0, 0.0, 0.0], [False] * 4) for t in range(5)]
    c = DiffChain.from_base(states[0], subject="s", checkpoint_interval=10)
    for s in states[1:]:
        c.append(s)
    return c


def test_verify_clean_is_match():
    v = _chain().verify()
    assert v.verdict == "MATCH" and v.broken_entry is None


def test_verify_detects_corrupted_diff():
    c = _chain()
    bad = dataclasses.replace(c.entries[2], result_sha="0" * 64)  # tamper a diff's result link
    c.entries[2] = bad
    v = c.verify()
    assert v.verdict == "UNVERIFIABLE" and v.broken_entry == 2


def test_verify_detects_corrupted_change_payload():
    c = _chain()
    bad = dataclasses.replace(c.entries[1], changes=((0, 99.0, False),))  # wrong change
    c.entries[1] = bad
    assert c.verify().verdict == "UNVERIFIABLE"


def test_throttled_tick_is_unverifiable_with_reason():
    c = DiffChain.from_base(_f([0.1, 0.2, 0.3, 0.4], [False] * 4), subject="s")
    d = c.append(throttle_reason="budget spent; identity changed but pixels not perceived")
    assert d.verdict == "UNVERIFIABLE" and d.throttle_reason
    assert c.current().verdict == "UNVERIFIABLE"
    # reconstructing the throttled tick yields an all-unknown field, never a guess
    r = c.reconstruct(c.tick)
    assert all(r.field.unknown)


def test_throttle_then_recovery_reconstructs():
    c = DiffChain.from_base(_f([0.1, 0.2, 0.3, 0.4], [False] * 4), subject="s")
    c.append(throttle_reason="throttled")                       # tick 1: all-unknown
    recovered = _f([0.5, 0.6, 0.7, 0.8], [False] * 4)
    c.append(recovered)                                         # tick 2: re-perceived
    assert c.reconstruct(2).state_sha == field_state_sha(recovered)
    assert c.verify().verdict == "MATCH"


def test_shape_change_reanchors_keyframe():
    c = DiffChain.from_base(_f([0.1, 0.2, 0.3, 0.4], [False] * 4, w=2, h=2), subject="s")
    bigger = _f([0.0] * 6, [False] * 6, w=3, h=2)
    d = c.append(bigger)
    from coherence_membrane.livestate import FieldSnapshot
    assert d.verdict == "DRIFT" and isinstance(c.entries[c.tick], FieldSnapshot)
    assert c.reconstruct(c.tick).state_sha == field_state_sha(bigger)
    assert c.verify().verdict == "MATCH"


import json
from pathlib import Path


def test_save_load_roundtrip_and_verify(tmp_path):
    states = [_f([float(t) / 10, 0.0, 0.0, 0.0], [False] * 4) for t in range(4)]
    c = DiffChain.from_base(states[0], subject="s", checkpoint_interval=2)
    for s in states[1:]:
        c.append(s)
    p = tmp_path / "chain.json"
    c.save(p)
    back = DiffChain.load(p)
    assert back.subject == "s" and back.tick == 3
    assert back.current().state_sha == field_state_sha(states[3])
    assert back.verify().verdict == "MATCH"
    assert back.reconstruct(3).state_sha == field_state_sha(states[3])


def test_load_handedited_chain_is_unverifiable(tmp_path):
    states = [_f([float(t) / 10, 0.0, 0.0, 0.0], [False] * 4) for t in range(4)]
    c = DiffChain.from_base(states[0], subject="s", checkpoint_interval=10)
    for s in states[1:]:
        c.append(s)
    p = tmp_path / "chain.json"
    c.save(p)
    data = json.loads(Path(p).read_text(encoding="utf-8"))
    # tamper a diff's change payload without fixing its result_sha
    for e in data["entries"]:
        if e["kind"] == "diff":
            e["changes"] = [[0, 42.0, False]]
            break
    Path(p).write_text(json.dumps(data), encoding="utf-8")
    assert DiffChain.load(p).verify().verdict == "UNVERIFIABLE"
