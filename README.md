<h1 align="center">axiomere-python</h1>

<p align="center">
  <strong>Axiomere from Python — the truth ledger where nothing is ever deleted.</strong>
</p>

<p align="center">
  🌐 <a href="https://axiovexsystems.com"><strong>axiovexsystems.com</strong></a>
  &nbsp;·&nbsp; Core (Rust): <a href="https://github.com/AXIOVEX/axiomere">AXIOVEX/axiomere</a>
</p>

[Axiomere](https://github.com/AXIOVEX/axiomere) is an append-only, signed, hash-chained record store designed for truthfulness, provenance, and change management. Records change only by appending new snapshots; withdrawal is a snapshot marked `dead`, reason on the record, score 0.0 — history stays fully readable. This package is the idiomatic Python API over the Rust core's PyO3 bindings.

## Install

The native extension is built from the core repository (a single bundled wheel distribution is on the roadmap):

```bash
pip install maturin
git clone https://github.com/AXIOVEX/axiomere
maturin develop -m axiomere/crates/axiomere-py/Cargo.toml   # builds `_axiomere`
pip install git+https://github.com/AXIOVEX/axiomere-python
```

## Use

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

Note what the API does not have: no `update`, no `delete` — in this package or in the core beneath it. That absence is the product.

## License

MIT. © 2026 Axiovex Systems, LLC. See [LICENSE](LICENSE).
