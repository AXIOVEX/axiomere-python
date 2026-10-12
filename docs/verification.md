# Verification

Verification is the operation the whole design exists to make cheap
and total. `ledger.verify()` (or `axiomere.verify_file(path)`,
standalone) re-walks the file and checks:

1. **The magic** — line 1 must be `AXMR1`.
2. **The hash chain** — every event's `hash` recomputed as
   `SHA-256(prev_hash ‖ canonical(event body))` over the canonical
   JSON encoding, and every `prev_hash` matched against its
   predecessor. Alteration, insertion, deletion, or reordering
   breaks verification at the first affected `seq`, with a named
   reason.
3. **Signatures** — each signed event's Ed25519 signature checked
   against the public key embedded in the event (self-consistency),
   counted in `signatures_checked` / `signatures_failed`.

The result:

```python
Verification(ok=True, events=3, break_seq=None, reason=None,
             signatures_checked=3, signatures_failed=0)
```

On failure, `ok` is `False`, `break_seq` names the first broken
sequence number, and `reason` names the failure (e.g.
`hash-mismatch`). The package's own test suite pins the behaviour: a
tampered file fails `verify_file`, and a ledger that fails
verification refuses to `open` for appends.

## What verification does and does not establish

- Verification establishes that **this file is exactly the history
  its chain commits to** — nothing was quietly altered after the
  fact.
- Signatures checked against embedded keys establish
  *self-consistency*. Checking them against a caller-supplied
  trusted-key map is what establishes *identity*.
- Verification alone does not protect against a sole-copy operator
  recomputing a chain from genesis. That is what **layer 5 —
  external anchoring** of Merkle checkpoint roots — is for: deposit
  the root where the operator does not control it (a DOI-minting
  repository, a timestamp authority, a transparency log), and
  tampering becomes evident to anyone. The core produces the roots
  and receipt data; anchor transport belongs to the embedding
  system, and a deployment that skips anchoring must say so.
