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

## Roadmap

- **Increment 1:** static-artifact perception — PNG identity, dimensions, perceptual
  hash, drift; the inert organ + selftest contract; `perceive()`; the write-gate bridge.
- **Increment 2:** the agnostic frame-handoff contract; native universal capture of the
  composited output (Windows/macOS/Linux via `ctypes`, no shims); the
  change-proportional, self-throttling continuity loop; consequence-scope.
- **Increment 3:** a second sense (`AudioArtifactOrgan`) on the same contract;
  modality-agnostic baseline memory (drift against an authorized baseline, persisted).
- **Increment 4 (this):** `LiveMembrane` — the living loop as one configurable object
  (perceive + remember + mediate consequence).
- **Next:** macOS/Linux on-platform validation (the author has Windows only — those
  backends are implemented to the OS APIs but unvalidated); a raw-frame fast path for
  high-rate capture; Wayland/PipeWire backend; structured-data organ.

## Install / test

```bash
pip install -e ".[test]"
python -m pytest          # 97 tests
python -m coherence_membrane selftest             # every sense proves itself
python -m coherence_membrane capture frame.png    # native screen grab
```

## License

MIT.
