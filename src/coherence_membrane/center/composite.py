"""The composite loop — generate -> render -> perceive -> reconcile, with REAL organs on both halves.

The atelier (generate-mind) produces a real artifact; it is rasterized (the atelier emits a point-recipe;
we draw it with coherence-membrane's own zero-dep PNG encoder — no SVG engine, no PIL); the eye
(perceive-mind) perceives THAT rendered artifact into a witnessed Observation; and a CompositeJudge
scores each candidate on BOTH halves — studio-engine's generative fitness AND the eye's perception
quality. The center then selects the best under the human's named criterion (which may weight generative
and perceptual dimensions together) and emits the spine Certificate. This is the render->critique creative
loop, both senses real and meeting in one verdict.

v1 rasterizes the `spiral` point-recipe (phyllotaxis); other recipe modes fall back to a faithful generic
scatter so the eye still perceives a real, distinct raster. studio_engine is optional (lazy import).
"""
from __future__ import annotations
import json
import math

from ..certificate import Certificate, Verdict
from ..pngencode import encode_png
from ..organs.visual import VisualArtifactOrgan
from .atelier import AtelierJudge, summarize_world, _require_studio, _seed
from .eye import EyeJudge, summarize_observation
from .criterion import CriterionSpec
from .loop import witness_candidates

COMPOSITE_DIMS = ("fitness", "structure", "perceived", "decoded", "confidence")


def rasterize_world(world, size: int = 128) -> bytes:
    """Draw the atelier's generated point-recipe to a PNG (zero-dep). Faithful to the actual geometry
    the generator specifies (the points), so the eye perceives the real artifact — not a proxy."""
    grid = bytearray(b"\xf7" * (size * size * 3))   # light background

    def plot(x: int, y: int, rgb):
        if 0 <= x < size and 0 <= y < size:
            i = (y * size + x) * 3
            grid[i], grid[i + 1], grid[i + 2] = rgb

    rp = world.layers[0].render_program
    recipe = rp.recipe
    count = int(recipe.get("count", 400))
    angle = math.radians(float(recipe.get("angle_deg", 137.5)))
    scale = float(recipe.get("scale", 5.0))
    cx = cy = size / 2.0
    maxr = scale * math.sqrt(max(1, count))
    fit = (size * 0.46) / maxr if maxr else 1.0
    for i in range(count):
        if recipe.get("mode") == "spiral":
            r = scale * math.sqrt(i) * fit
            th = i * angle
        else:                                        # generic faithful scatter from the recipe values
            r = (size * 0.46) * ((i * 2654435761) % 1000) / 1000.0
            th = i * angle
        x = int(cx + r * math.cos(th))
        y = int(cy + r * math.sin(th))
        c = int(255 * i / max(1, count))
        plot(x, y, (20, c, 255 - c))
    return encode_png(size, size, bytes(grid), 3)


class CompositeJudge:
    """Scores each candidate on BOTH halves: generative fitness (from the World, via AtelierJudge) and
    perception quality (from the Observation of its render, via EyeJudge). The two senses meet here."""

    def __init__(self, world_store: dict, obs_store: dict):
        self._gen = AtelierJudge(world_store)
        self._eye = EyeJudge(obs_store)

    def score(self, candidate: str, subject_views, dims=COMPOSITE_DIMS) -> dict:
        merged = {**self._gen.score(candidate, subject_views, ("fitness", "structure", "passes_fitness")),
                  **self._eye.score(candidate, subject_views, ("perceived", "decoded", "confidence"))}
        return {d: merged.get(d, 0.0) for d in dims}


def composite_reconcile(brief: str, criterion: CriterionSpec, *, generator: str = "phyllotaxis",
                        seeds=(1, 2, 3), max_steps: int = 8, size: int = 128,
                        eye_organ=None, dims=COMPOSITE_DIMS):
    """Generate several artifacts, render+perceive each, judge on both halves, select under the criterion.
    Each candidate is a real generated World AND a real witnessed perception of its render."""
    se = _require_studio()
    eye_organ = eye_organ or VisualArtifactOrgan()
    world_store: dict = {}
    obs_store: dict = {}
    candidates: dict[str, str] = {}
    for s in seeds:
        world = se.simulate(seed=(_seed(brief) ^ int(s)), generator=generator, max_steps=max_steps)
        png = rasterize_world(world, size)
        observed = eye_organ.observe(png)
        obs = observed[0] if observed else None
        text = (f"[composite:{generator}#{s}] atelier generated {summarize_world(world)} "
                f"|| eye perceives {summarize_observation(obs) if obs is not None else 'nothing'}")
        world_store[text] = world
        if obs is not None:
            obs_store[text] = obs
        candidates[f"{generator}#{s}"] = text
    return witness_candidates(candidates, {"brief": brief}, criterion, CompositeJudge(world_store, obs_store), dims)


def _variant_seed(base: int, r: int, i: int) -> int:
    return (base ^ (r * 1000003) ^ (i * 97)) & 0x7FFFFFFF


def iterative_refine(brief: str, criterion: CriterionSpec, *, generator: str = "phyllotaxis",
                     rounds: int = 5, variants: int = 4, patience: int = 2, max_steps: int = 8,
                     size: int = 128, eye_organ=None, dims=COMPOSITE_DIMS) -> Certificate:
    """The true loop: generate -> render -> perceive -> (the composite score, which INCLUDES the eye's
    perception, drives the next generation) -> regenerate around the current best -> repeat. Hill-climbs
    the named criterion until no round improves it (patience). The eye's perception genuinely feeds back
    — a variant the eye perceives poorly scores lower and is not adopted. Returns a Certificate carrying
    the refined winner + the witnessed trajectory (monotone non-decreasing by construction).
    """
    se = _require_studio()
    eye_organ = eye_organ or VisualArtifactOrgan()
    world_store: dict = {}
    obs_store: dict = {}
    candidates: dict[str, str] = {}

    def make(label: str, seed: int) -> None:
        world = se.simulate(seed=seed, generator=generator, max_steps=max_steps)
        png = rasterize_world(world, size)
        observed = eye_organ.observe(png)
        obs = observed[0] if observed else None
        text = (f"[{label}] atelier generated {summarize_world(world)} "
                f"|| eye perceives {summarize_observation(obs) if obs is not None else 'nothing'}")
        world_store[text] = world
        if obs is not None:
            obs_store[text] = obs
        candidates[label] = text

    def weighted(label: str) -> float:
        judge = CompositeJudge(world_store, obs_store)
        return criterion.score(judge.score(candidates[label], {"brief": brief}, dims))

    base = _seed(brief)
    make("r0", base)
    cur_label, cur_seed, cur_w = "r0", base, weighted("r0")
    trajectory = [round(cur_w, 6)]
    improvements = stale = rounds_run = 0
    for r in range(1, rounds + 1):
        rounds_run = r
        improved = False
        for i in range(variants):
            label = f"r{r}.{i}"
            seed = _variant_seed(cur_seed, r, i)         # explore AROUND the current best
            make(label, seed)
            w = weighted(label)
            if w > cur_w + 1e-9:                          # adopt only improvements -> monotone climb
                cur_label, cur_seed, cur_w, improved = label, seed, w, True
        trajectory.append(round(cur_w, 6))
        if improved:
            improvements += 1
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                break

    final = CompositeJudge(world_store, obs_store).score(candidates[cur_label], {"brief": brief}, dims)
    evidence = (
        ("criterion", criterion.name),
        ("criterion_dims", json.dumps(criterion.normalized().dims)),
        ("winner", cur_label),
        ("winner_weighted", str(round(cur_w, 6))),
        ("rounds_run", str(rounds_run)),
        ("improvements", str(improvements)),
        ("trajectory", json.dumps(trajectory)),
        ("final_scores", json.dumps(final)),
    )
    return Certificate(f"refined best under '{criterion.name}' over {rounds_run} rounds (+{improvements} improvements)",
                       Verdict.VERIFIED, "neutral-center-refine-v1", evidence)


def trajectory_of(cert: Certificate) -> list:
    return json.loads(dict(cert.evidence).get("trajectory", "[]"))
