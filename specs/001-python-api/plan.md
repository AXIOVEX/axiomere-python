# Spec 001 — Plan (as-built)

**Date:** 2026-10-12 · Companion to `spec.md`.

```
_ Axiomere extension contract (from AXIOVEX/axiomere crates/axiomere-py)
Database wrapper + Verification dataclass + module functions   [src/axiomere/__init__.py]
Pytest suite against the real extension (no mocks of the core)  [tests/test_axiomere.py]
CI: checkout core -> maturin build wheel -> install -> pytest   [.github/workflows/ci.yml]
```

## Decisions recorded

- The wrapper returns core JSON events as parsed dicts rather than inventing a parallel event model — one model, owned by the core.
- The bindings crate carries a crate-local `pyproject.toml` in the core repo pinning the wheel/module name; CI history (three failed runs, 2026-10-11) records why: maturin adopts ancestor project metadata otherwise.
- Tests run against the *real* extension built from the core repo in CI, so a core/wrapper contract break fails this repo's CI, not a user's install.
