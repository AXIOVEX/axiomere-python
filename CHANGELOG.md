# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A multi-platform wheel-building workflow (cibuildwheel across Linux, Windows, and macOS), prepared for future releases; its first practice run is in progress, and one Linux build leg failed and is being diagnosed.

## [0.1.0] - 2026-10-13

### Added

- The pure-Python `axiomere` package, published to PyPI: a Python wrapper over the Axiomere append-only ledger — create keypairs, append signed events, take a snapshot, and verify a record on its own.
- Importing the package without the native extension installed stops with an error that explains how to build it — no silent fallback, by design.
- Regression tests proving that numbers with 17 significant digits survive a write/read round trip exactly.

The published files for v0.1.0 were built from commit `ad885bd`; released 2026-10-13.
