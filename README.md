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
- Capture is the **operator's** responsibility and must be of a source the operator
  **owns or has authorised**. This tool reads artifact bytes you hand it; it never
  reaches into another process.

## Roadmap

- **Increment 1 (this):** static-artifact perception — PNG identity, dimensions,
  perceptual hash, drift; the inert organ + selftest contract; `perceive()`; the
  write-gate bridge.
- **Next:** more organs (other formats, audio, structured data) on the same contract;
  a live capture adapter (the inert save→observe→restore interception pattern) for
  operator-owned render surfaces; richer drift baselines.

## Install / test

```bash
pip install -e ".[test]"
python -m pytest          # 47 tests
python -m coherence_membrane selftest
```

## License

MIT.
