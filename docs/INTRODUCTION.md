# Introduction to Coherence Membrane

Coherence Membrane is a zero-dependency Python library that lets an AI agent,
a test harness, or any host program perceive real local state instead of
guessing at it. It turns files, PNGs, WAVs, JSON documents, captions, and live
screen frames into structured observations carrying exact SHA-256 identities,
witnessed dimensions, and 64-bit perceptual fingerprints. It compares those
observations against operator-authorized baselines and returns a closed
verdict: MATCH, DRIFT, or UNVERIFIABLE, never a silent pass.

The entire trust path is the Python standard library. Screen capture goes
through the OS compositor via `ctypes`, so it works under D3D, Vulkan, OpenGL,
Metal, and software renderers without importing a graphics API.

## Why it exists

A language model reasons on its prior and on source text, not on what actually
happened at runtime. "This frame renders correctly" is, structurally, a guess
dressed as a fact. The membrane replaces the guess with a witnessed,
re-derivable observation the model can ground on, which is the same move twice:
it stops an agent acting on a hallucination, and it finally closes the make,
look, compare, adjust loop the agent was always blind in.

## Core concepts

**Observation.** The unit of perception. Every observation carries the
full-width SHA-256 of the exact bytes it saw, modality-specific facts (width
and height, audio envelope hash, canonical JSON identity, glyph grid), and a
status. An unreadable or malformed artifact yields an unverified observation
with no fabricated data.

**Organ.** A single sense with a contract: it reads, it reports, it never
mutates anything, and it ships a `selftest()` that re-derives its own claims
from a known artifact and can fail. Sixteen organs are registered by default,
covering sight, hearing, structured data, captions, region drift, glyph views,
contours, palettes, raw frames, and six deductive verifiers.
`python -m coherence_membrane selftest` runs them all and exits non-zero if
any organ cannot prove itself.

**Drift lattice.** Every adjudicator returns a verdict from a small closed
set. MATCH requires positive evidence, absence of evidence is UNVERIFIABLE,
and contrary evidence is DRIFT. These laws are not docstrings: `lattice.py`
proves them by exhaustive enumeration on every `pytest` run, including that
composing verdicts can never turn a worse set into a better one.

**Baseline.** Operator-authorized memory. Pin an observation, then check later
observations against it on a three-rung ladder: byte identity, canonical
(normal-form) identity, perceptual distance. A reformatted JSON document is a
MATCH; a changed value is a DRIFT. Baselines persist to disk.

**Continuity.** The always-on loop. A cheap identity hash runs every tick;
only a real change escalates to the full perceptual work, and a
`ResourceBudget` caps and paces that work. A change the budget cannot afford
is reported UNVERIFIABLE("throttled"), never dropped.

**Receipt and provenance.** `emit_receipt` wraps an observation's facts with a
content anchor the operator pins or signs out-of-band; `verify_receipt`
re-derives and checks it. `ProvenanceGraph` chains observations, actions, and
gate decisions into a hash-bound DAG where tampering any surviving node breaks
everything downstream.

**The two gates.** This repo is the read-gate: what is actually there? Its
complement, [proof-surface](https://github.com/HarperZ9/proof-surface), is the
write-gate: may this action proceed? They compose through a shared JSON shape,
not a dependency, so each is useful alone.

## Your first ten minutes

Install from source (Python 3.10+, no runtime dependencies):

```bash
git clone https://github.com/HarperZ9/coherence-membrane
cd coherence-membrane
python -m pip install -e ".[test]"
```

1. Make the membrane prove itself before you trust it:

```bash
python -m coherence_membrane selftest
```

Expect a JSON report with `"passed": true` and one entry per organ. A
membrane that cannot verify itself refuses, by exit code, to be trusted.

2. Perceive something real. Grab your own screen, then observe the file:

```bash
python -m coherence_membrane capture shot.png
python -m coherence_membrane perceive shot.png
```

The perceive output shows the identity hash, the dimensions, and the
perceptual hash. Run it twice: the identity is bit-stable. Only use capture on
surfaces you own or are authorized to inspect.

3. Detect drift from Python:

```python
from coherence_membrane import perceive, Baseline

obs = perceive(["shot.png"]).observations[0]
b = Baseline()
b.pin(obs)                                   # authorize this state
b.check(obs).verdict                         # MATCH
# edit or re-capture shot.png, then:
b.check(perceive(["shot.png"]).observations[0]).verdict   # DRIFT
```

4. Watch live state change-proportionally:

```bash
python -m coherence_membrane watch 30 --raw
```

One JSON event per frame. Unchanged frames cost an identity hash; a real
change reports a perceptual distance. The `--raw` flag skips PNG encoding
entirely and is the path to use at high rates.

5. Verify a deductive claim instead of trusting an assertion:

```python
from coherence_membrane import PropositionalVerifierOrgan
from coherence_membrane.propositional import Var, And, Implies

A, B = Var("A"), Var("B")
obs = PropositionalVerifierOrgan().observe(Implies(And(A, Implies(A, B)), B))[0]
obs.data["verdict"]   # "verified"
```

An oversized or undecidable claim comes back UNVERIFIABLE. The verifier
organs never return a false verdict to stay helpful.

## Where to go next

- The [README](../README.md) has the full capability list, the CLI table, and
  the honest-limits section.
- [USAGE.md](../USAGE.md) states the public boundary in five lines.
- [ROADMAP.md](../ROADMAP.md) shows what is planned, with explicit flags for
  anything that cannot be validated on the author's Windows-only machine.
- `conformance/run.py` and `impl/js/run.js` re-derive the frozen 16-case
  contract corpus in Python and Node.js respectively; `schemas/` holds the
  JSON Schemas for the wire shapes.
- The test suite (`python -m pytest`, 914 passing) is the most precise
  documentation of behavior, including the machine-checked lattice proofs in
  `tests/test_lattice.py` and `tests/test_lattice_binding.py`.

One closing note on the point of it all: every claim the membrane makes is
designed to be re-derived by someone who does not trust it. The hashes are
full-width, the corpus is frozen, a second implementation in another language
agrees value-for-value, and the safety laws are enumerated rather than
promised. Perception you cannot re-check is just another assertion.
