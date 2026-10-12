# axiomere-python — Project Constitution

**Version:** 1.0.0 · **Ratified:** 2026-10-12 · **Owner:** Tristen Pierson, Axiovex Systems, LLC

This package is the Python face of Axiomere. Its constitution is short because its job is narrow: expose the truth ledger's guarantees to Python *without diluting them*. The Axiomere constitution (AXIOVEX/axiomere) governs the store; these articles govern the wrapper. Development follows the spec-kit + AEE flow.

## Article I — No new powers

The wrapper exposes what the core provides and nothing more. In particular it must never grow a convenience the core forbids: no update, no delete, no "admin" escape hatch, no silent fallback store. If a capability is not in the Rust core's public API, it does not appear here.

## Article II — No fake fallbacks

If the native extension is unavailable, import fails loudly with build instructions. The package never substitutes a pure-Python reimplementation that would let a user believe they hold Axiomere's guarantees (hash chain, signatures, checkpoints) when they hold an imitation.

## Article III — Errors stay truthful

Core verification failures surface as errors carrying the core's reason (sequence, failure kind). The wrapper does not catch, soften, or retry-around a verification failure: a broken ledger is evidence, and Python code must be able to see that plainly.

## Article IV — Claims carry falsifiers

Every spec ships an AEE claims bundle in engine format, each claim naming its falsifier, with an assessment produced by actually running the assessor. Build-ahead-of-claims deviations are recorded in the assessment that catches up, per the Axiomere constitution's Article VII.
