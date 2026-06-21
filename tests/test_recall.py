from __future__ import annotations

from coherence_membrane.certificate import Certificate, Verdict
from coherence_membrane.reconcile import Criterion
from coherence_membrane.memory import MemoryRecord, MemoryStore, CriterionRef, PerceiveRef
from coherence_membrane.registries import CriterionRegistry, PerceiverRegistry
from coherence_membrane.recall import verify_fresh
from coherence_membrane.phash import MATCH, DRIFT, UNVERIFIABLE


def _source_backed(claim, expect_value):
    # a memory whose truth is re-read from a (mock) source and judged equal to expect
    return MemoryRecord(
        id="m", type="pointer", claim=claim,
        criterion_ref=CriterionRef("equals", "v1", (("expect", expect_value),)),
        perceive_ref=PerceiveRef("source", (("value", claim),)),
    )


def _registries(current_source_value):
    crits = CriterionRegistry()
    # criterion: VERIFIED iff the perceived form == "match"
    crits.register(Criterion("equals", lambda form:
        Certificate(str(form), Verdict.VERIFIED if form == "match" else Verdict.REFUTED, "equals-v1")),
        version="v1")
    percs = PerceiverRegistry()
    # perceiver re-reads the (mock) live source; "match" if it equals the pinned expectation
    percs.register("source", lambda args: (
        "match" if current_source_value == "blue" else "changed",
        current_source_value.encode(),
    ))
    return crits, percs


def test_source_unchanged_is_match():
    s = MemoryStore(); r = _source_backed("blue", "blue"); s.remember(r)
    crits, percs = _registries(current_source_value="blue")
    assert verify_fresh(r, s, criteria=crits, perceivers=percs)[0] == MATCH


def test_source_changed_is_drift():
    s = MemoryStore(); r = _source_backed("blue", "blue"); s.remember(r)
    crits, percs = _registries(current_source_value="red")  # live source moved
    assert verify_fresh(r, s, criteria=crits, perceivers=percs)[0] == DRIFT


def test_unregistered_criterion_is_unverifiable():
    s = MemoryStore(); r = _source_backed("blue", "blue"); s.remember(r)
    assert verify_fresh(r, s, criteria=CriterionRegistry(), perceivers=PerceiverRegistry())[0] == UNVERIFIABLE


def test_graph_backed_supersession():
    s = MemoryStore()
    old = MemoryRecord(id="old", type="decision", claim="use X")
    s.remember(old)
    s.remember(MemoryRecord(id="new", type="decision", claim="use Y"),
               parents=("old",), edge_type="supersedes")
    assert verify_fresh(old, s)[0] == DRIFT       # superseded
    new = s.get("new")
    assert verify_fresh(new, s)[0] == MATCH        # not superseded, no source
