# Axiomere (Python)

**A truth ledger where nothing is ever deleted.**

[Axiomere](https://github.com/AXIOVEX/axiomere) is an append-only,
signed, hash-chained record store designed for truthfulness,
provenance, and change management. Records change only by appending
new snapshots; withdrawal is a snapshot marked `dead`, its reason on
the record, its score set to 0.0 — history stays fully readable.

This package is the idiomatic Python API over the Rust core's PyO3
bindings. The core implements the integrity layers; this package wraps
them without weakening them — including the defining absence:

> Note what the API does not have: **no `update`, no `delete`** — in
> this package or in the core beneath it. That absence is the product.

## The integrity layers

1. **SHA-256 hash chain** over canonical event encodings: every event
   carries `seq`, `prev_hash`, and its own hash; alteration,
   insertion, deletion, or reordering breaks verification at the
   first affected `seq`, with a named reason.
2. **Content-addressed snapshots** with parent links — a git-like
   lineage where each snapshot's ancestry is tamper-evident
   independently of the event chain.
3. **Ed25519 signed appends** — actor keys; the event carries the
   signer public key and the signature over the event hash.
4. **Signed Merkle checkpoints** over event ranges — a compact
   commitment to a whole history.
5. **External anchoring** of checkpoint roots (the caller's
   transport): layers 1–4 make tampering evident to the operator;
   anchoring makes it evident to *anyone*.

A ledger that fails verification **refuses to open for appends** — a
broken record is evidence, never a writing surface.

## Install

```bash
pip install axiomere
```

The native extension is built from the core repository (a single
bundled wheel distribution is on the roadmap). From source:

```bash
pip install maturin
git clone https://github.com/AXIOVEX/axiomere
maturin develop -m axiomere/crates/axiomere-py/Cargo.toml   # builds `_axiomere`
pip install git+https://github.com/AXIOVEX/axiomere-python
```

Importing the package without its native extension raises
`ImportError` with build instructions. There is no pure-Python
fallback, by constitution: a ledger that silently degraded to an
unverified store would be worse than one that fails loudly.

## Quick example

```python
import axiomere

seed, public = axiomere.generate_keypair()          # Ed25519 actor key
ledger = axiomere.Database.create("study.axmr", seed_hex=seed)

ledger.snapshot("claim-1", {"text": "X holds"}, actor="researcher", score=0.8)
ledger.snapshot("claim-1", {"text": "X holds, narrowed"}, actor="researcher", score=0.6)
ledger.dead("claim-1", reason="retracted", actor="adjudicator")

ledger.current()                    # {} — dead excluded by default
ledger.current(include_dead=True)   # the record, its death, its reason
result = ledger.verify()            # Verification(ok=True, events=3, signatures_checked=3, ...)
ledger.checkpoint(actor="researcher")   # Merkle checkpoint over the range
```

## Where next

- [The `.axmr` format](format.md) — one file, one magic line,
  canonical JSON events.
- [Python API](api.md) — the full surface of this package.
- [Verification](verification.md) — what `verify()` checks, and what
  a failure means.
- [Float canonicalization](float-canonicalization.md) — the 1-ULP
  defect that made honest ledgers fail verification, and its fix.

## License

MIT. © 2026 Axiovex Systems, LLC. See the `LICENSE` file in this
repository. The Rust core
([AXIOVEX/axiomere](https://github.com/AXIOVEX/axiomere)) is MIT as
well.
