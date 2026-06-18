# coherence-membrane

**An inert, host-adjudicated perception membrane — the read-gate that gives a model
real, witnessed eyes, and the read-gate complement to
[proof-surface](https://github.com/HarperZ9/proof-surface)'s write-gate.**

A model's one structural disability is **state-blindness**: it reasons on its prior
and on source text, not on what actually happened. When it says "this frame renders
correctly" or "this file contains X," that is a *guess about runtime state dressed as
a fact*. The membrane's job is to replace the guess with a **witnessed, re-derivable
observation** the model can ground on — so it reasons on observed inputs and measured
outputs instead of simulating the world in its head.

The same grounding is the safety and the capability. A model that perceives true,
re-derivable state can't act on a hallucination (safety) **and** can finally close the
make → look → compare → adjust loop it was always blind in (capability). That dual use
— in the good sense — is the whole target.

## The two gates

| Gate | Repo | Question it answers |
| --- | --- | --- |
| **Read-gate** (this repo) | `coherence-membrane` | "What is *actually* there?" — perceive real artifacts into witnessed Observations. |
| **Write-gate** | `proof-surface` (`pre_execution_gate`) | "May this action proceed, given that state?" — default-deny, advisory. |

They are deliberately **separate repos**: a read-gate is useful to specs that never
act; a write-gate is useful to agents with no eyes. They compose through the shared
observation/receipt JSON shape, not through a dependency.

## What it does (increment 1)

A stdlib-only PNG perception path:

```python
from coherence_membrane import perceive, VisualArtifactOrgan, compare_drift

snap = perceive(["frame.png"])              # inert: reads, never writes
obs = snap.observations[0]
obs.data["identity_sha256"]                 # exact, full-width, re-derivable
obs.data["width"], obs.data["height"]       # witnessed dimensions
obs.data["perceptual_hash"]                 # 64-bit dHash of the decoded pixels
```

Drift against a baseline, as a closed lattice (mirroring EMET):

```python
verdict = compare_drift(baseline_sha, current_sha, baseline_phash, current_phash)
verdict.verdict   # MATCH | DRIFT | UNVERIFIABLE   (never a silent match on difference)
```

The perceived state then flows out through the write-gate:

```python
from coherence_membrane import build_gate_request, decide
req = build_gate_request(action_kind="render_read", target="frame.png",
                         authorization=receipt, drift=verdict)
decide(req)   # -> proof-surface GateDecision (allow/deny/needs-human), or
              #    needs-human if the write-gate isn't installed (fail-closed)
```

A `DriftVerdict`'s `MATCH/DRIFT/UNVERIFIABLE` *is* the gate's `witness_verdict`
lattice, so perceived visual drift flows straight into the gate's state check.

## Live capture (increment 2) — native, universal, no shims

The architecture for capturing live frames is **dependency inversion: don't hook
the world, capture what it already composited.** Every renderer — D3D11, D3D12,
Vulkan, OpenGL, Metal, software — composites to the display. Capturing *there* is
agnostic to all of them by construction: the membrane never imports a graphics
API, never tracks a D3D version, and needs no producer-side shim. It asks the OS
for the pixels the OS already has, through the OS's own API via `ctypes` (stdlib —
no third-party package).

| Platform | Backend | Status |
| --- | --- | --- |
| Windows | GDI (`BitBlt` + `GetDIBits`) | **validated live** |
| macOS | CoreGraphics (`CGDisplayCreateImageForRect`) | implemented to the API; validate on-platform |
| Linux / X11 | Xlib (`XGetImage`) | implemented to the API; validate on-platform |

```bash
python -m coherence_membrane capture frame.png   # one native grab of the screen
python -m coherence_membrane watch 30             # always-on perception, 30 frames
```

```python
from coherence_membrane import ScreenCaptureSource, ResourceBudget, run_continuity
src = ScreenCaptureSource(region=(0, 0, 1280, 720))   # any owned/authorised surface
for event in run_continuity(src, budget=ResourceBudget(min_interval_s=0.2), max_frames=300):
    event.verdict     # MATCH (cheap) / DRIFT / UNVERIFIABLE (throttled)
    event.distance    # perceptual distance on a real visual change
```

**Always-on without being over-consumptive.** The continuity loop is
*change-proportional*: a cheap identity hash runs every tick; only a real change
escalates to the full decode + perceptual hash. A `ResourceBudget` caps the
expensive work and paces the cadence; once spent, a changed frame is reported
`UNVERIFIABLE("throttled")` — never silently dropped.

**Mediate consequence, not activity.** The loop only *perceives*; it never gates.
Acting goes through the write-gate, and only for consequential actions:

```python
from coherence_membrane import creative_profile
scope = creative_profile()
scope.requires_gate("publish")   # True  — consequential, gate it
scope.requires_gate("draw")      # False — reversible/local, flows free
```

So creative and gamedev flow is frictionless by construction: perception is
continuous and free; only `publish`/`export`/`overwrite`/`spend`/`delete`/`send`/
`deploy` touch the gate, and the operator can widen or narrow that set.

## A second sense, and baseline memory (increment 3)

Perception is not only sight. The same inert observe→witness contract extends to
**hearing**: `AudioArtifactOrgan` perceives a WAV (stdlib `wave`, no third-party
audio stack) — identity, format, and a 64-bit perceptual fingerprint of the
loudness envelope — and fails closed to identity-only on anything it can't decode.

```python
from coherence_membrane import AudioArtifactOrgan, all_organs
AudioArtifactOrgan().observe("clip.wav")[0].data["perceptual_audio_hash"]
```

**Baseline memory** turns frame-to-frame drift into accountability over time:
pin an authorized observation, then check later observations against it. It is
modality-agnostic — one baseline covers frames and sounds alike — and returns the
same `MATCH` / `DRIFT` / `UNVERIFIABLE` lattice.

```python
from coherence_membrane import Baseline
b = Baseline(); b.pin(authorized_observation)   # the operator authorises a state
b.check(later_observation).verdict              # MATCH | DRIFT | UNVERIFIABLE
b.save("baseline.json")                          # drift is tracked across runs
```

## The living loop (increment 4)

`LiveMembrane` ties it together into one operator-configured object: it perceives
continuously, remembers an authorized baseline, and mediates **only consequence**.
It adds no authority and removes no check — every guarantee still lives in the
parts it composes.

```python
from coherence_membrane import LiveMembrane, ScreenCaptureSource
m = LiveMembrane()                                   # defaults: creative profile
for event in m.perceive(ScreenCaptureSource(), max_frames=300):
    ...                                              # free, continuous perception
m.authorize(some_observation)                        # operator pins the baseline
m.propose("draw", "canvas").decision                 # "allow" — reversible, un-gated
m.propose("publish", "site", authorization=receipt)  # routed to the write-gate
```

## The raw-frame fast path (increment 5) — high-rate, encode-free

`ScreenCaptureSource` PNG-encodes every grab so each frame is witnessable on
disk. At high capture rates that encode is pure overhead — the OS already handed
over raw pixels. `RawScreenCaptureSource` skips it: each frame carries the raw
BGRA bytes plus geometry, the continuity loop hashes those bytes for identity
every tick, and **only a real change** pays the perceptual hash — computed
directly from the raw pixels (`RawFrameOrgan`), with no PNG encode and no decode,
ever.

```python
from coherence_membrane import RawScreenCaptureSource, run_continuity, ResourceBudget
src = RawScreenCaptureSource(region=(0, 0, 1280, 720))   # raw BGRA, no per-frame encode
for event in run_continuity(src, budget=ResourceBudget(min_interval_s=0.1), max_frames=600):
    event.verdict     # MATCH (cheap identity hash) / DRIFT / UNVERIFIABLE
    event.distance    # perceptual distance on a real change — from raw pixels
# The loop selects RawFrameOrgan automatically for raw frames; no organ to pass.
```

The load-bearing guarantee, proven in the organ's selftest: the raw fast path
yields the **bit-identical** perceptual hash to the encode→decode path for the
same pixels. It changes the cost, never the answer.

```bash
python -m coherence_membrane watch 60 --raw   # always-on perception, fast path
```

| Path | Per-frame work (unchanged frame) | Per-frame work (changed frame) |
| --- | --- | --- |
| `ScreenCaptureSource` (PNG) | capture + convert + **zlib encode** + identity hash | + decode + perceptual hash |
| `RawScreenCaptureSource` (raw) | capture + identity hash | + convert + perceptual hash (**no encode/decode**) |

Illustrative single-run figures (one Windows machine, 640×480 region, median of
40 grabs): `grab_raw` ≈ 8 ms vs `grab_png` ≈ 20 ms per grab — and unchanged
frames skip all perceptual work entirely. Re-derive your own with
`python scripts/bench_raw_vs_png.py`; the point measurement is reproducible
rather than asserted.

## A third sense, and canonical drift (increment 6)

Sight and hearing perceive pixels and sound. `StructuredDataOrgan` perceives
**data** — a JSON document the operator owns or has authorised (stdlib `json`,
no third-party parser). It witnesses two identities: the raw bytes, and a
**canonical** identity — the digest of the document re-serialised in a normal
form (sorted keys, no insignificant whitespace).

```python
from coherence_membrane import StructuredDataOrgan
obs = StructuredDataOrgan().observe(b'{"b": 2, "a": 1}')[0]
obs.data["identity_sha256"]    # the exact bytes
obs.data["canonical_sha256"]   # the document's normal form, hashed
```

Why two hashes: for an image, byte drift *is* the change. For data it is too
sensitive — reformatting or reordering keys flips the raw identity while the
document is unchanged. So **baseline memory now checks on a three-rung ladder**:
byte identity → canonical (normal-form) identity → perceptual distance. A
reformatted-but-equivalent document is a `MATCH`; a changed value is a real
`DRIFT`; array order stays significant because it is meaningful.

```python
from coherence_membrane import Baseline
b = Baseline(); b.pin(StructuredDataOrgan().observe(b'{"a": 1, "b": 2}')[0])
b.check(StructuredDataOrgan().observe(b'{ "b": 2, "a": 1 }')[0]).verdict   # MATCH (reformatted)
b.check(StructuredDataOrgan().observe(b'{"a": 1, "b": 3}')[0]).verdict     # DRIFT (value changed)
```

This is **structural** canonicalisation (key order + whitespace + escaping), not
an understanding of content: canonical-equal is a sufficient-but-not-necessary
proxy for "the same data" — equal canonical forms are genuinely equivalent, but
values that *mean* the same can still differ canonically. It normalises key order
and whitespace and escapes non-ASCII, but does **not** normalise numeric spelling
(`1` vs `1.0`) or representation (`1e3` vs `1000`), and it inherits IEEE-754 float
limits — extreme magnitudes can round (e.g. `1e-400` → `0.0`), so the canonical
form reflects the *parsed* float, which may not equal the source literal.
`-0.0` and `0.0` differ; duplicate keys collapse to the last value (RFC-8259
parse). A value with no canonical form (`NaN`/`Infinity`) fails closed to
identity-only — never a fabricated canonical hash. Canonicalisation runs entirely
in memory with no size cap (peak RAM is a small multiple of the document size);
bound the artifact size upstream before observing untrusted input.

## The agent loop (increment 7) — make → look → compare → adjust

A state-blind model *reasons* about whether its action worked; the agent loop lets
it *check*. The agent **makes** (produces an artifact), the membrane **looks**
(perceives the result) and **compares** it to the intended goal, and recommends
**adjust** or **converged** — purely advisory iteration control, never gated. The
one consequential step, **committing** the result, routes through the write-gate,
measuring drift against the operator-**authorized** baseline (the baseline ladder:
byte identity → canonical → perceptual).

```python
from coherence_membrane import AgentLoop, Goal
loop = AgentLoop(Goal.from_observation(reference_obs, tolerance=4))
for proposal in loop.iterate(agent.make, max_iterations=10):  # agent makes; loop looks
    proposal.disposition         # "adjust" ... until "converged"
loop.authorize()                                 # operator approves the converged result
loop.commit("publish", "site/index.html", authorization=receipt).decision
#   "allow"        — result matches the approved baseline, grant valid
#   "deny"         — result drifted from what was approved (gate sees the DRIFT)
#   "needs-human"  — committed with no look, or no authorized baseline (fail-closed)
```

Two comparisons, deliberately separate so nothing is laundered: the **goal +
tolerance** governs *when to stop iterating* (advisory, never touches the gate);
the **commit** measures the result against the *authorized* baseline (identical
bytes — or, for structured data, a canonically-equivalent form), so a model can
never publish something that doesn't match what it set out to make without the
gate seeing exactly that. The membrane never makes and never actuates — it
perceives, compares, and recommends; the operator/runtime commits.

## Finer eyes, an external anchor, and a contract (increment 8)

Three advances that deepen the read-gate's granularity, trust, and credibility.

**Region/element perception — *where* it changed.** `RegionArtifactOrgan` emits
the same whole-image facts (so it still slots into baseline memory and the gate)
plus a row-major grid of per-tile dHashes; `compare_region_drift` localises a
change to the tiles that actually moved.

```python
from coherence_membrane import RegionArtifactOrgan, compare_region_drift
a = RegionArtifactOrgan(rows=4, cols=4).observe("before.png")[0]
b = RegionArtifactOrgan(rows=4, cols=4).observe("after.png")[0]
compare_region_drift(a.data["region_hashes"], b.data["region_hashes"], 4, 4).changed_regions
# -> [5]   the change is isolated to tile 5, not "the whole screen changed"
```

**Signed observation receipts — the external anchor across the seam.** A bare
SHA-256 is keyless self-consistency, not tamper-evidence. A `WitnessReceipt` wraps
an observation's witnessed facts with a content hash (its `anchor`); the operator
pins that anchor out-of-band (and may sign it), and `verify_receipt` re-derives
and checks it — a closed `VALID / DRIFT / UNVERIFIABLE` lattice, fail-closed.

```python
from coherence_membrane import emit_receipt, verify_receipt
receipt = emit_receipt(observation)
anchor = receipt.anchor()                         # operator pins / signs this
verify_receipt(receipt, pinned_anchor=anchor).verdict   # VALID
verify_receipt(receipt).verdict                          # UNVERIFIABLE (no anchor — honest)
```

**Conformance vectors + a wire spec — re-derivability made *demonstrable*.**
`conformance/vectors.json` is a frozen, hash-pinned corpus; `conformance/run.py`
re-derives every case through this implementation; `schemas/` holds JSON Schemas
for the `Observation` and `DriftVerdict` wire shapes. A second, independent
JavaScript implementation (`impl/js/`) now re-derives the **same** corpus — so
re-derivability is **demonstrated, not asserted** (increment 9).

```bash
python conformance/run.py     # all cases re-derive; corpus hash pinned
```

## Re-derivability, demonstrated (increment 9)

A second implementation, in JavaScript (`impl/js/membrane.js`), sharing **no code**
with the Python reference (Node built-ins only — `crypto`, `zlib`), independently
re-derives every value in `conformance/vectors.json`: SHA-256, PNG-decode + dHash,
the drift lattice, canonical-JSON, region drift, and the receipt anchor. The
Python suite runs the JS harness and checks the two agree **value-for-value**.

```bash
node impl/js/run.js     # {"impl":"js","cases":16,"passed":16,"failed":0}
```

This retires the honest caveat increment 8 shipped with: a witness two independent
implementations agree on — across the **frozen contract corpus** — is a *proof*,
not a claim. It is also the on-ramp for the JS-native worlds (editors, CI, Node
tooling) that need the inert read core without a Python runtime — and deliberately
does **not** port native capture, which is OS-specific and unvalidatable off the
author's platform.

**Known fidelity boundary (honest).** The demonstration is over the corpus, not a
proof of total equivalence. The one place the two languages can't trivially agree
is numbers: a JSON float like `1.0` parses to the integer `1` in JS, and JS can't
reproduce Python's float repr. So the JS `canonical()` **throws** on any
non-safe-integer number rather than silently diverging — floats and integers
beyond 2⁵³ are out of the JS core's contract (the corpus uses only safe integers).
Strings, bools, null, arrays, objects, PNG-decode + dHash, the drift/region
lattices, and receipt anchors agree exactly.

## Design discipline (encoded, not asserted)

- **Inert.** Organs read and report. They never mutate the artifact, the process that
  produced it, or anything else. A test asserts observing a file leaves its bytes
  unchanged.
- **Advisory, never authority.** There is no `TRUSTED`/`APPROVED` status. The organ
  reports; a host re-derives and adjudicates.
- **Witnessed, not inferred.** Every observation carries the **full-width** SHA-256 of
  the bytes it saw (no truncation — the digest is the trust anchor).
- **Selftest or net-negative.** Every organ ships a `selftest()` that re-derives its
  own claims from a known artifact and can fail. *An unverified membrane is worse than
  none — it launders falsehood with ground-truth authority.* `python -m
  coherence_membrane selftest` exits non-zero if any organ can't prove itself.
- **Fail-closed.** An unreadable file or an unsupported/malformed PNG yields an
  `unverified` observation with no perceptual hash — never a crash, never a fabricated
  hash.

## Honesty about what it is

- The SHA-256 and the dHash are **keyless self-consistency** — re-derivable integrity,
  not non-repudiable identity and not tamper-evidence against an adversary who
  recomputes them. Anti-forgery needs an external anchor (a signed/pinned digest); the
  write-gate is where that belongs.
- A dHash is a coarse 64-bit fingerprint of low-frequency structure, **not** a semantic
  understanding of the image. Distance is advisory evidence.
- Capture reads the **composited display output** the operator can already see, via
  the OS's own screen API — it does **not** inject into, hook, or read another
  process's memory, and it must be used only on surfaces the operator owns or has
  authorised. It is perception of the screen, not intrusion into a program.
- The **raw identity** (SHA-256 of BGRA bytes) is *not* equal to the **PNG identity**
  for the same pixels — they are different byte streams. Only the *perceptual
  fingerprint* is comparable across the raw and PNG paths; a baseline pinned on raw
  frames matches raw frames, and one pinned on PNGs matches PNGs. This is stated,
  and tested, rather than glossed.

## Roadmap

- **Increment 1:** static-artifact perception — PNG identity, dimensions, perceptual
  hash, drift; the inert organ + selftest contract; `perceive()`; the write-gate bridge.
- **Increment 2:** the agnostic frame-handoff contract; native universal capture of the
  composited output (Windows/macOS/Linux via `ctypes`, no shims); the
  change-proportional, self-throttling continuity loop; consequence-scope.
- **Increment 3:** a second sense (`AudioArtifactOrgan`) on the same contract;
  modality-agnostic baseline memory (drift against an authorized baseline, persisted).
- **Increment 4:** `LiveMembrane` — the living loop as one configurable object
  (perceive + remember + mediate consequence).
- **Increment 5:** the raw-frame fast path — `grab_raw` /
  `RawScreenCaptureSource` (encode-free native capture), `RawFrameOrgan`
  (perceptual hash straight from raw pixels), and `perceptual_hash_raw`; the
  continuity loop auto-selects the raw organ for raw frames. Bit-identical to the
  PNG path, proven by selftest; validated live on Windows.
- **Increment 6:** a third sense — `StructuredDataOrgan` (JSON) with a
  canonical (normal-form) identity; baseline memory generalised to a three-rung
  ladder (byte identity → canonical identity → perceptual distance), so drift on
  structured data is measured on the document's normal form, not its raw bytes.
- **Increment 7:** the agent loop — `AgentLoop` / `Goal` /
  `AdjustmentProposal`: make → look → compare → adjust as a real, grounded loop,
  with the one consequential commit routed through the write-gate against the
  authorized baseline (allow / deny / needs-human, fail-closed).
- **Increment 8:** finer eyes, an external anchor, and a contract —
  `RegionArtifactOrgan` + `compare_region_drift` (where it changed), `WitnessReceipt`
  + `verify_receipt` (a pinned/signed anchor across the read→write seam), and a
  hash-pinned conformance corpus + JSON-Schema wire spec (re-derivability made
  demonstrable — a second implementation is what proves it).
- **Increment 9 (this):** a second-language (JavaScript) reference core
  (`impl/js/`) that independently re-derives the conformance corpus —
  re-derivability **demonstrated**: two implementations sharing no code agree,
  value-for-value, on the frozen contract corpus (with an honest, fail-loud number
  boundary so they never silently diverge beyond it).
- **Next:** see [ROADMAP.md](ROADMAP.md) for the full plan. Near/mid-term:
  temporal perception (`EventTrace` — drift episodes over time), multimodal fusion
  (`CompositeObservation`), a causal/temporal provenance DAG, and TLA+ proofs of
  the verdict lattices.
  `[unvalidatable-here]`: macOS/Linux/Wayland capture validation (the author has
  Windows only — those backends are implemented to the OS APIs but unvalidated).

## Install / test

```bash
pip install -e ".[test]"
python -m pytest          # 206 tests
python conformance/run.py                         # the read-gate wire contract (Python)
node   impl/js/run.js                             # the SAME contract, re-derived in JS
python -m coherence_membrane selftest             # every organ proves itself
python -m coherence_membrane capture frame.png    # native screen grab
python -m coherence_membrane watch 60 --raw       # always-on perception, fast path
```

## License

MIT.
