from __future__ import annotations

from coherence_membrane.pngencode import encode_png
from coherence_membrane.retro import render_vintage
from coherence_membrane.render_critic import render_fidelity_deviation


def _gradient_png(w=32, h=32) -> bytes:
    """A deterministic horizontal RGB gradient PNG (something to quantize)."""
    rows = bytearray()
    for y in range(h):
        for x in range(w):
            rows.extend((int(255 * x / (w - 1)), int(255 * y / (h - 1)), 128))
    return encode_png(w, h, bytes(rows), channels=3)


def test_fidelity_faithful_lower_than_aggressive():
    src = _gradient_png()
    faithful = render_vintage(src, target_width=32, palette_k=16, dither=True, scanlines=False)
    aggressive = render_vintage(src, target_width=4, palette_k=2, dither=False, scanlines=True)
    dev_faithful = render_fidelity_deviation((src, faithful.output_png))
    dev_aggressive = render_fidelity_deviation((src, aggressive.output_png))
    assert dev_faithful >= 0.0
    assert dev_faithful < dev_aggressive   # a faithful render is structurally closer to the source


def test_fidelity_identity_is_near_zero():
    # comparing a render to itself (as both source and output) is ~0 deviation
    src = _gradient_png()
    r = render_vintage(src, target_width=32, palette_k=16, scanlines=False)
    assert render_fidelity_deviation((r.output_png, r.output_png)) < 1e-9


from coherence_membrane.render_critic import render_signature, critique_render


def test_signature_is_stable_int():
    src = _gradient_png()
    r = render_vintage(src, target_width=16, palette_k=8, scanlines=False)
    s1 = render_signature(r.output_png)
    s2 = render_signature(r.output_png)
    assert isinstance(s1, int) and s1 == s2


def test_empty_corpus_is_unverifiable():
    src = _gradient_png()
    r = render_vintage(src, target_width=16, palette_k=8, scanlines=False)
    obs = critique_render(r, src, corpus=[], min_distance=5, tolerance=0.2)
    assert obs.data["verdict"] == "unverifiable"   # novelty UNVERIFIABLE -> composite UNVERIFIABLE


def test_derivative_render_is_refuted():
    src = _gradient_png()
    r = render_vintage(src, target_width=16, palette_k=8, scanlines=False)
    corpus = [render_signature(r.output_png)]          # the render is already in the corpus
    obs = critique_render(r, src, corpus=corpus, min_distance=5, tolerance=1.0)
    assert obs.data["verdict"] == "refuted"            # distance 0 < min_distance -> REFUTED, absorbing


def test_novel_and_fit_is_verified():
    src = _gradient_png()
    r = render_vintage(src, target_width=32, palette_k=16, scanlines=False)
    far_corpus = [0]                                   # a hash far from the render's signature
    obs = critique_render(r, src, corpus=far_corpus, min_distance=1, tolerance=10.0)
    assert obs.data["verdict"] == "verified"           # novel AND within a lax fidelity tolerance


def test_unfit_render_is_refuted():
    src = _gradient_png()
    r = render_vintage(src, target_width=4, palette_k=2, dither=False, scanlines=True)
    obs = critique_render(r, src, corpus=[0], min_distance=1, tolerance=0.001)
    assert obs.data["verdict"] == "refuted"            # novel but deviation > tiny tolerance


from coherence_membrane.memory import MemoryStore
from coherence_membrane.render_critic import remember_render, render_corpus


def test_remember_then_corpus_includes_signature():
    src = _gradient_png()
    r = render_vintage(src, target_width=16, palette_k=8, scanlines=False)
    store = MemoryStore()
    assert render_corpus(store) == []                       # empty to start
    obs = critique_render(r, src, corpus=[], min_distance=5, tolerance=1.0)
    remember_render(store, r, obs)
    corpus = render_corpus(store)
    assert render_signature(r.output_png) in corpus         # the remembered render is now in the corpus


def test_corpus_makes_a_repeat_derivative():
    src = _gradient_png()
    r = render_vintage(src, target_width=16, palette_k=8, scanlines=False)
    store = MemoryStore()
    remember_render(store, r, critique_render(r, src, corpus=[], min_distance=5, tolerance=1.0))
    # the SAME render, judged against the now-populated corpus, is derivative
    obs2 = critique_render(r, src, corpus=render_corpus(store), min_distance=5, tolerance=1.0)
    assert obs2.data["verdict"] == "refuted"
