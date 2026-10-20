# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-10-20

### Added

- A verification policy for `Database.verify()` and `axiomere.verify_file()`, matching the core's Spec 003 (verification policy). Pass `trusted={actor: public_key_hex}` to check signatures against your own key map — the identity check: every actor must be named in the map and every event signed with that actor's key, and the result names any actor the map does not cover. Pass `expected_head={...}` to pin the end of the ledger (last event's hash, minimum event count, latest checkpoint root) — the only way a shortened copy of a ledger is caught, since a shorter copy is still a valid chain on its own. Verification also gains the checks the policy adds underneath: checkpoint roots are recomputed rather than taken from the file's own claim, and a signed ledger fails if any of its events is missing its signature.
- Regression tests for the verification policy at the Python surface: a checkpoint root transplanted from another ledger fails even when re-signed by its true author, stripped signatures fail, an actor missing from the trusted map is reported by name, a truncated ledger fails under a head pin, and values that cannot be stored exactly are refused.

### Changed

- `axiomere.verify_file()` now returns the full `Verification` result — the same eight fields `Database.verify()` returns, including the list of unsigned events and any untrusted actors — instead of a three-item `(ok, count, reason)` tuple. A malformed or unreadable file comes back as a failed result with a named reason instead of raising or answering in part.
- (2026-10-13) The wheel workflow now builds the extension against one pinned Axiomere core commit — `cc452998c7bdbdd3fae50964733fef5f9bed0d3e`, the Spec 003 verification-policy build — instead of whatever core main happened to be at run time, so a release's core is a recorded fact rather than an accident of timing. The pinned commit lives in the workflow file; there is no clean way to stamp it into the wheel metadata itself, because the build tool takes wheel metadata from the core repository's own manifests.
- (2026-10-20) For this 0.2.0 release, the pinned core commit moves to `f685e58a5670e29f706b6f0201ba0d8f1e5ab137` — the Axiomere 0.2.0 release commit (tag `v0.2.0` in the core repository) — and the wrapper was re-tested against it before release.
- (2026-10-13) Every GitHub Action used by this repository's workflows is pinned by commit SHA, with the version it was resolved from kept as a comment. That includes the publish action, which previously floated on the `release/v1` branch name inside the job that holds the publish permission.
- (2026-10-13) The wheel workflow's smoke test now runs a real signed round trip — create a ledger under a fresh key, append an event, take a snapshot, checkpoint, then verify with signatures checked and verify the written file standalone — instead of only importing the extension and generating a keypair.

### Fixed

- Appending a payload that carries a value which cannot be stored exactly — NaN, positive or negative infinity, or an integer outside the exactly representable range — now raises `ValueError` and appends nothing. Before, the native extension silently stored NaN as null and rounded very large integers, so the file on disk was not what the caller submitted.

- The wheel workflow's Linux setup now installs a small system library (libatomic) that the Rust installer needs inside the 32-bit build container — without it, that build stopped before compiling anything.
- The Intel Mac build now uses GitHub's current Intel runner (macos-15-intel) instead of the retired macos-13, which left builds waiting forever.
- The Intel Mac wheel build now sets its minimum macOS version to 10.12, matching what the compiled extension actually requires — before this, the build aimed at an older minimum (10.9) than the extension allows, and the wheel repair step refused to finish it.

## [0.1.0] - 2026-10-13

### Added

- The pure-Python `axiomere` package, published to PyPI: a Python wrapper over the Axiomere append-only ledger — create keypairs, append signed events, take a snapshot, and verify a record on its own.
- Importing the package without the native extension installed stops with an error that explains how to build it — no silent fallback, by design.
- Regression tests proving that numbers with 17 significant digits survive a write/read round trip exactly.

The published files for v0.1.0 were built from commit `ad885bd`; released 2026-10-13.
