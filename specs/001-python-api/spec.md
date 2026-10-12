# Spec 001 — Python API v0.1 (as-built record)

**Date:** 2026-10-12 · **Status:** Implemented (v0.1, shipped 2026-10-11) · **Process note:** written in the 2026-10-12 spec-kit + AEE catch-up, after the v0.1 build; the deviation is recorded here and in the assessment, per Constitution Article IV. From Spec 002 onward, claims precede code.

## 1. What was built

The idiomatic Python package `axiomere` (src layout, hatchling) wrapping the Rust core's PyO3 extension `_axiomere` (built from AXIOVEX/axiomere `crates/axiomere-py`): a `Database` class (create/open, optional Ed25519 seed), `snapshot()`, `dead()`, `checkpoint()`, `current()`, `events()`, `verify()` returning a `Verification` dataclass, plus module-level `generate_keypair()` and `verify_file()`.

## 2. Requirements

- **FR-APY-01** The API exposes no update or delete operation (Constitution Article I).
- **FR-APY-02** Without the native extension, import raises ImportError with build instructions — never a fallback implementation (Article II).
- **FR-APY-03** A ledger that fails verification refuses to open, surfacing the core's reason as a ValueError (Article III).
- **FR-APY-04** Dead semantics round-trip: a record withdrawn via `dead()` is absent from `current()`, present in `current(include_dead=True)` with status dead, score 0.0, and its reason.
- **FR-APY-05** Signed operation: with a seed, appends are signed and `verify()` reports signatures checked/failed counts from the core.
- **FR-APY-06** CI builds the bindings from AXIOVEX/axiomere and runs the test suite against them on every push.

## 3. Non-goals (v0.1)

No bundled-wheel distribution yet (install builds the extension from the core repo — documented in the README, roadmap item); no async API; no pandas/ORM integrations.

## 4. Verification

5 pytest tests (lineage/view folding, dead semantics, signed appends, tampered-file `verify_file`, broken-log open refusal), green locally and in GitHub CI.
