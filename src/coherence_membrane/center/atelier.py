"""AtelierMind — the atelier (studio-engine) wired as the center's GENERATE mind.

The atelier is the generative half of the reconcile (the eye is the perceptive half). Here it plugs
into the center behind the `Mind` interface: instead of *reasoning* a text proposal, it GENERATES a
real artifact (a studio-engine World/Scene — phyllotaxis, gyroid, quasicrystal, …) from a seed derived
from the subject view, and contributes a faithful text representation of that generated artifact as its
proposal. On reconcile, it regenerates informed by the other minds' deposits (perturbed seed / chosen
generator). Its sense IS generation.

Optional dependency: `studio_engine`. The center core does not require it; importing this module without
studio_engine raises a clear error only when an AtelierMind is actually used.
"""
from __future__ import annotations
import json
import zlib


def _require_studio():
    try:
        import studio_engine as se  # noqa: F401
        return se
    except ImportError as e:  # pragma: no cover - environment-dependent
        raise ImportError(
            "AtelierMind needs the `studio_engine` package on the path "
            "(the atelier / studio-engine repo). Install or add it to PYTHONPATH."
        ) from e


def _seed(text: str) -> int:
    return zlib.adler32(text.strip().encode("utf-8")) & 0x7FFFFFFF


def summarize_world(world) -> str:
    """A faithful, deterministic text representation of a generated World: its title, each layer's
    generator + recipe (the generative parameters that ARE the artifact), and its palette."""
    parts = [f"title={world.title!r}"]
    for layer in world.layers:
        rp = getattr(layer, "render_program", None)
        if rp is not None:
            recipe = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in rp.recipe.items()}
            parts.append(f"layer[{layer.role or layer.organ_id}] generator={rp.generator} "
                         f"recipe={json.dumps(recipe, sort_keys=True)}")
    if getattr(world, "palette", None):
        parts.append(f"palette={list(world.palette)[:6]}")
    return "; ".join(parts)


class AtelierMind:
    """A center Mind whose proposals are real studio-engine generations."""

    def __init__(self, name: str = "atelier", generator: str = "phyllotaxis", max_steps: int = 8):
        self.name = name
        self.channel = "generate"
        self.generator = generator
        self.max_steps = max_steps

    def _generate(self, seed: int, generator: str | None = None) -> str:
        se = _require_studio()
        world = se.simulate(seed=seed, generator=generator or self.generator, max_steps=self.max_steps)
        return summarize_world(world)

    def perceive_and_propose(self, view: str) -> str:
        return f"[generate] atelier proposes a generated artifact: {self._generate(_seed(view))}"

    def reconcile(self, own_view: str, others_deposits: list[str]) -> str:
        # let the others' deposits perturb the seed (the meeting genuinely changes what is generated)
        seed = _seed(own_view + " || " + " | ".join(others_deposits))
        return (f"[generate|reconciled] atelier regenerates, informed by the other minds: "
                f"{self._generate(seed)}")
