"""Render-critic — wire the vintage renderer to the grounded critic + memory.

render -> perceive -> critique(compose[novelty vs corpus, structural fitness =
OKLab-dE source-vs-output fidelity]) -> remember, as a generator yielding witnessed
step events. Composes shipped parts; retro.py untouched. Stdlib only; inert.
"""
from __future__ import annotations

from .certificate import Verdict
from .color import delta_e_ok
from .color_field import color_field_from_png, downscale_color_field
from .composition import compose
from .memory import MemoryRecord, MemoryStore
from .novelty import novelty_criterion
from .observation import Observation, Provenance, Status
from .phash import hamming, perceptual_hash
from .pngview import decode_png
from .structural_fitness import structural_fitness_criterion

FIDELITY_CW = 64


def render_fidelity_deviation(form) -> float:
    """Mean OKLab dE between source and output, downscaled to a common grid.
    `form = (source_png, output_png)`. inf when nothing comparable (fail-closed)."""
    source_png, output_png = form
    src = color_field_from_png(source_png)
    out = color_field_from_png(output_png)
    cw = min(src.width, out.width, FIDELITY_CW)
    ch = max(1, round(cw * src.height / src.width))
    ch = min(ch, src.height, out.height)
    s = downscale_color_field(src, cw, ch)
    o = downscale_color_field(out, cw, ch)
    diffs = [delta_e_ok(s.lab[i], o.lab[i]) for i in range(cw * ch)
             if not s.unknown[i] and not o.unknown[i]]
    if not diffs:
        return float("inf")
    return sum(diffs) / len(diffs)


def render_signature(output_png: bytes) -> int:
    """The novelty signature of a render: 64-bit dHash of its output PNG."""
    return perceptual_hash(decode_png(output_png))


def critique_render(render_result, source_png, *, corpus, min_distance, tolerance) -> Observation:
    """Judge a render novel-vs-corpus AND structurally faithful; one witnessed Observation."""
    signature = render_signature(render_result.output_png)
    deviation = render_fidelity_deviation((source_png, render_result.output_png))
    nov = novelty_criterion(corpus, distance=hamming, min_distance=min_distance).judge(signature)
    # judge the precomputed deviation (constant measure -> no double compute)
    fit = structural_fitness_criterion(lambda _f: deviation, tolerance=tolerance).judge(None)
    cert = compose([nov, fit], claim="render is novel AND structurally faithful")
    decided = cert.verdict in (Verdict.VERIFIED, Verdict.REFUTED)
    return Observation(
        "render-critic", render_result.output_sha256, f"render critique: {cert.verdict.value}",
        Status.PASS if decided else Status.UNVERIFIED,
        Provenance.witness_bytes(render_result.output_sha256, render_result.output_png,
                                 "high" if decided else "low"),
        {"verdict": cert.verdict.value,
         "evidence": [list(e) for e in cert.evidence],
         "signature": signature, "deviation": deviation,
         "palette_hex": list(render_result.palette_hex)},
    )


def remember_render(store: MemoryStore, render_result, observation, *, source_id=None) -> str:
    """Store a render-look as a witnessed memory; its signature joins the corpus."""
    record = MemoryRecord(
        id=render_result.output_sha256,
        type="pref",
        claim=render_result.output_sha256,
        tags=("render",),
    )
    edges = ()
    if source_id is not None and source_id in store.records:
        edges = (source_id,)
    store.remember(record, parents=edges, edge_type="derived-from")
    # stash the recall-relevant signature/verdict on the store-side record map
    store.records[record.id] = record
    _RENDER_SIGS.setdefault(id(store), {})[record.id] = (
        observation.data["signature"], observation.data["verdict"],
        tuple(observation.data["palette_hex"]),
    )
    return record.id


# render signatures are perceptual hashes, not part of the canonical MemoryRecord
# identity (which is stdlib-serialisable); keep them in a side index keyed by store.
_RENDER_SIGS: dict[int, dict[str, tuple]] = {}


def render_corpus(store: MemoryStore) -> list[int]:
    """Perceptual signatures of all remembered renders in this store = the novelty corpus."""
    return [sig for (sig, _v, _p) in _RENDER_SIGS.get(id(store), {}).values()]
