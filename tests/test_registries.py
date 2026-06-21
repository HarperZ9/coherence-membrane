from __future__ import annotations

from coherence_membrane.reconcile import Criterion
from coherence_membrane.certificate import Certificate, Verdict
from coherence_membrane.registries import CriterionRegistry, PerceiverRegistry


def _crit(name="origin"):
    return Criterion(name, lambda form: Certificate(str(form), Verdict.VERIFIED, "origin-v1"))


def test_criterion_register_and_get_by_name_version():
    reg = CriterionRegistry()
    reg.register(_crit(), version="v1")
    assert reg.get("origin", "v1") is not None
    assert reg.get("origin", "v2") is None       # version-scoped
    assert reg.get("missing", "v1") is None


def test_perceiver_register_and_get():
    reg = PerceiverRegistry()
    reg.register("echo", lambda args: (args, str(args).encode()))
    fn = reg.get("echo")
    assert fn({"x": "1"}) == ({"x": "1"}, b"{'x': '1'}")
    assert reg.get("missing") is None
