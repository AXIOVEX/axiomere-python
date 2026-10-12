# Float canonicalization: the 1-ULP defect

Canonical JSON is the encoding hashes are defined over, so a float
must parse back to the **identical** value it was written as — or an
untampered ledger fails its own verification.

## The defect

The core's reader once read decimals needing ≥17 significant digits
back **one smallest step too high** (1 ULP — one unit in the last
place, the finest step the number format can take) — serde_json
without its `float_roundtrip` feature
does not guarantee correctly rounded parsing. The consequence was
the worst kind for a truth ledger: a log written honestly, through
this very package, **failed hash verification on reopen**, with no
tampering anywhere. The failure was first hit downstream — an
embedding system's ledger carrying a high-precision timestamp float.

## The fix

The core enables serde_json's `float_roundtrip` feature
(correctly rounded float parsing), so a written float re-reads
bit-identically and the canonical encoding — and therefore every
hash — is stable across write/read round trips. The fix landed in
the core as its Spec 002 (float canonicalization), with the affected
historical ledgers re-verified identically after it.

## The regression, pinned on this side

This package carries the companion regression
(`tests/test_float_roundtrip.py`):

- The exact downstream reproduction payload
  (`{"ts_like": 1791810119.6349843, "plain": 0.5}`) must verify on
  reopen.
- A sweep of the characterized trigger class — finite floats whose
  shortest decimal form needs ≥17 significant digits, plus boundary
  shapes (`0.30000000000000004`, `5e-324`, `−0.0`, …) — must verify
  on reopen.

The tests have teeth: against a pre-fix core build, every one of
them fails — `Database.open` raises `verification failed at seq 1:
hash-mismatch`, and in-session `verify()` already reports false. If
the defect ever silently returns, this package's suite says so
first.

## Practical note for embedders

Until an embedding system rebuilds its native extension from the
fixed core, it is running the pre-fix reader. Tekmerion's platform
ledger, for example, keeps a whole-second-timestamp discipline as
its guard until its next extension rebuild — timestamps with
sub-second float precision are exactly the trigger class.
