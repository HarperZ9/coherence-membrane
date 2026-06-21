"""novelty — a reconcile criterion for grounded creative novelty.

The Cell *Patterns* result (Dec 2025): naive generate->describe->regenerate loops
collapse to a handful of generic motifs ("visual elevator music") because the critic
is an ungrounded caption. The cure is a SPECIFIC, grounded criterion: judge a work's
perceived signature against the WITNESSED CORPUS of prior work — VERIFIED-novel only
if it is far from everything seen, REFUTED-derivative if it collapses onto something.
This is the creativity surface as a reconcile criterion (perceive the shape with an
organ; judge novelty here). Generic over the signature type + distance metric — a
perceptual hash + hamming is the shipped instantiation; the caller injects both, so
this module stays uncoupled from any particular organ."""
from __future__ import annotations

from .certificate import Certificate, Verdict
from .reconcile import Criterion

_ORACLE = "novelty-vs-corpus-v1"


def novelty_criterion(corpus, *, distance, min_distance) -> Criterion:
    """A Criterion judging a signature NOVEL iff its minimum distance to every corpus
    signature is >= min_distance. VERIFIED-novel / REFUTED-derivative / UNVERIFIABLE
    (empty corpus, or a distance that fails to compute). `distance(a, b)` is a
    caller-supplied metric over signatures (e.g. hamming over perceptual hashes);
    `corpus` is the witnessed set of prior-work signatures."""
    corpus = tuple(corpus)

    def judge(signature) -> Certificate:
        if not corpus:
            return Certificate("novelty (empty corpus)", Verdict.UNVERIFIABLE, _ORACLE,
                               (("reason", "no corpus to compare against"),))
        try:
            nearest = min(distance(signature, c) for c in corpus)
        except Exception as exc:
            return Certificate("novelty", Verdict.UNVERIFIABLE, _ORACLE, (("reason", repr(exc)),))
        verdict = Verdict.VERIFIED if nearest >= min_distance else Verdict.REFUTED
        claim = f"novel: nearest-corpus-distance {nearest!r} >= {min_distance!r}"
        return Certificate(claim, verdict, _ORACLE,
                           (("nearest_distance", repr(nearest)),
                            ("min_distance", repr(min_distance)),
                            ("corpus_size", str(len(corpus)))))

    return Criterion("novelty-vs-corpus", judge)
