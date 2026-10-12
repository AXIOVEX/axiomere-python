# Spec 001 — Tasks (as-built, all complete at v0.1)

- [x] T101 `Database` wrapper (create/open ± seed) over `_axiomere.PyLedger` + seed helpers.
- [x] T102 `Verification` dataclass + `verify_file` + `generate_keypair` module functions.
- [x] T103 Import guard: missing extension raises ImportError with build instructions (no fallback).
- [x] T104 Pytest suite (5 tests) against the real extension.
- [x] T105 CI: cross-repo bindings build + test, green on GitHub.
- [x] T106 README with install path (maturin build from the core repo) + usage.
- [ ] T107 Bundled-wheel distribution (single `pip install axiomere` with prebuilt wheels) — future spec.
