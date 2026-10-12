# AEE Assessment — Spec 001 Python API (after_implement)

**Date:** 2026-10-12 · **Tooling:** spec-kit 1.0.10, AEE extension v1.2.0, AEE engine 1.0.4, threshold 0.70
**Claims assessed:** 6 (`aee-claims.json` v0.1.0) · **Machine record:** `aee-assessment.json`
**Outcome: ITERATE** — the shipped wrapper carries its claims; the only sub-threshold claim is a future distribution improvement, labeled a draft.

| Claim | Score | State |
|-------|-------|-------|
| APY-001-01 no update/delete in the Python API | 0.85 | supported — public surface |
| APY-001-02 no fake fallback: import fails loudly without the extension | 0.85 | supported — import guard |
| APY-001-03 broken ledgers refuse to open; core reason surfaces | 1.00 | supported — tamper + refusal tests |
| APY-001-04 dead semantics round-trip (audit view: dead, reason, 0.0) | 0.90 | supported — dead test |
| APY-001-05 seeded appends are signed; verify reports core counts | 0.90 | supported — signing test |
| APY-001-06 single-command pip install (bundled wheels) | 0.48 | **draft** — T107, future spec; README states the two-step build openly |

## Reading

The wrapper's constitutional risks are dilution risks — a convenience the core forbids, a fallback that fakes the guarantee, an error that hides a verification failure. The claims target exactly those, and each is pinned by a test against the *real* extension (CI builds it from the core repo; nothing is mocked). ITERATE reflects one honest draft (distribution), not a defect in what shipped.

*Process note:* v0.1 was built 2026-10-11 before this repo had a spec-kit scaffold — recorded deviation (Constitution Article IV). This catch-up (2026-10-12) installed the full flow; it governs from Spec 002 onward.

## Addendum — 2026-10-12: float-roundtrip companion (AXIOVEX/axiomere Spec 002 §7)

The core's Spec 002 fixed a reader-side float defect: serde_json's default parser read back decimals needing ≥ 17 significant digits 1 ULP high, so untampered logs carrying such floats failed hash verification on reopen — the failure Tekmerion's platform ledger hit downstream. The §7 companion item for this repo is discharged on branch `companion/float-roundtrip-regression`:

- **Build:** no code, API, or dependency-pin change in this package. The workflow checks out AXIOVEX/axiomere `main` unpinned, and that main now carries the fix at `40d6933` (serde_json `float_roundtrip` enabled in the core and bindings crates). The local verification build pinned its core checkout to `40d6933` explicitly and followed the workflow's maturin route.
- **Regression test:** `tests/test_float_roundtrip.py` (2 tests) appends the exact downstream reproduction `{"ts_like": 1791810119.6349843, "plain": 0.5}` plus a sweep of trigger-class floats (≥ 17-significant-digit plain and exponent forms, smallest/largest finite, smallest subnormal, integral-valued, signed zero), then requires `Database.open`, `verify()`, and `verify_file` all to pass with bit-exact read-back, and the reopened log to stay appendable. Full suite: **7 passed** against the fixed core.
- **Teeth check:** the same two tests were run against a wheel built from the pre-fix core (`43d4cbc`): both fail with the defect's exact signature (`verify()` already false in-session; `hash-mismatch` at seq 1). The regression cannot pass vacuously on an unfixed core.
- **Claim effect:** none re-scored, no claim status changed. The tests stand as observed evidence for the wrapper's verify-on-reopen behavior (sound logs open and verify; APY-001-03 covers the refusal side). Tekmerion-side environments pick the fix up on their next extension rebuild. No release was cut — publishing remains owner-gated.
