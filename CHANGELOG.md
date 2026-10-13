# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A multi-platform wheel-building workflow (cibuildwheel across Linux, Windows, and macOS), prepared for future releases.

### Fixed

- The wheel workflow's Linux setup now installs a small system library (libatomic) that the Rust installer needs inside the 32-bit build container — without it, that build stopped before compiling anything.
- The Intel Mac build now uses GitHub's current Intel runner (macos-15-intel) instead of the retired macos-13, which left builds waiting forever.
- The Intel Mac wheel build now sets its minimum macOS version to 10.12, matching what the compiled extension actually requires — before this, the build aimed at an older minimum (10.9) than the extension allows, and the wheel repair step refused to finish it.

## [0.1.0] - 2026-10-13

### Added

- The pure-Python `axiomere` package, published to PyPI: a Python wrapper over the Axiomere append-only ledger — create keypairs, append signed events, take a snapshot, and verify a record on its own.
- Importing the package without the native extension installed stops with an error that explains how to build it — no silent fallback, by design.
- Regression tests proving that numbers with 17 significant digits survive a write/read round trip exactly.

The published files for v0.1.0 were built from commit `ad885bd`; released 2026-10-13.
