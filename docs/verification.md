# Verification

Verification is the operation the whole design exists to make cheap
and total. Call it on an open ledger —

```python
result = ledger.verify()
```

— or on a file by path, with no ledger object needed:

```python
result = axiomere.verify_file("study.axmr")
```

Both return the same result object, with the same eight fields on
every surface (this package, the file check, the core's command-line
tool):

```python
Verification(ok=True, events=3, break_seq=None, reason=None,
             signatures_checked=3, signatures_failed=0,
             unsigned_events=(), untrusted_actors=())
```

| Field | Meaning |
|---|---|
| `ok` | Did the ledger pass every check? |
| `events` | How many events were read. |
| `break_seq` | On failure, the sequence number where verification stopped. |
| `reason` | On failure, a short name for what failed (for example `hash-mismatch`). |
| `signatures_checked` | How many events carried a signature that was checked. |
| `signatures_failed` | How many of those signatures failed their check. |
| `unsigned_events` | The sequence numbers of events that carry **no** signature. Reported in every mode, pass or fail — see below. |
| `untrusted_actors` | Actors a trusted-mode check refused to vouch for — see below. |

## What is checked

Verification re-walks the file and checks:

1. **The magic and the exact bytes** — line 1 must be `AXMR1`, and
   every event line must be byte-for-byte the canonical encoding of
   the event it parses to. A line that merely *parses* to the right
   event — respelled numbers, reordered keys, an extra field, a
   duplicated key, Windows line endings — fails with
   `non-canonical-line`. The file a person inspects and the file the
   verifier checked are the same bytes.
2. **The hash chain** — every event's `hash` recomputed as
   `SHA-256(prev_hash ‖ canonical(event body))`, and every
   `prev_hash` matched against its predecessor. Alteration,
   insertion, deletion, or reordering of events breaks verification
   at the first affected `seq`, with a named reason.
3. **Checkpoint roots, recomputed** — a checkpoint claims a Merkle
   root over the events it closes. Verification never takes the
   claim's word for it: it recomputes the root from the actual event
   hashes and fails with `checkpoint-root-mismatch` if they differ.
   (Before this check existed, a forged history could carry the real
   root copied in from the honest ledger and pass — including against
   the externally anchored value.)
4. **Snapshot lineage and withdrawal rules** — every snapshot's id
   is recomputed from its content and parent, parents must be real
   earlier snapshots of the same record, a `dead` snapshot must carry
   a non-empty reason and a score of exactly 0.0, and no live
   snapshot may follow a dead one for the same record.
5. **Signature presence** — next section.
6. **Signatures** — each signed event's Ed25519 signature, checked
   according to the mode below.

## Signature presence: missing is reported, and often fatal

A signature that is *absent* cannot fail a signature check — so
presence is checked separately, and the findings are always on the
face of the result:

- `unsigned_events` lists every event that carries no signature, in
  every mode, whether verification passes or fails. An honestly
  unsigned ledger verifies in bare mode with `signatures_checked`
  0 and every sequence number listed — a visible state, never a
  silent one.
- If a ledger carries signatures at all, then every event must carry
  one. Stripping the signature from even one event of a signed
  ledger fails verification with `unsigned-event` — the downgrade
  attack (strip the signatures, keep the content) no longer works.
- In trusted mode (below), an unsigned event fails regardless.

## Two modes: bare and trusted

`verify()` and `verify_file()` both accept a `trusted` argument,
and it selects what signatures are checked *against*:

- **`trusted=None` (the default) — bare mode.** Signatures are
  checked against the public keys embedded in the events themselves.
  This establishes *self-consistency*: the file is exactly the
  history its chain commits to, and each signed event was signed by
  the holder of the key it carries. It does not establish *who*
  anybody is — a key proves itself.
- **`trusted={"alice": public_key_hex, ...}` — trusted mode.** This
  is the identity check. Every event's actor must appear in the map,
  and every event must be signed with that actor's mapped key. An
  event by an actor the map does not name fails verification with
  `untrusted-actor`, and the actor is reported in
  `untrusted_actors`; there is no fallback to trusting the key
  embedded in the event. A mapped actor signing with the *wrong* key
  fails with `signer-key-mismatch`.
- **`trusted={}` is a real choice, not a missing argument.** An
  empty map trusts nobody, so every event fails as untrusted. `None`
  and `{}` mean different things, and the difference is deliberate:
  only `None` asks for self-consistency alone.

```python
seed, public = axiomere.generate_keypair()
ledger = axiomere.Database.create("study.axmr", seed_hex=seed)
# … appends, signed by the key above …
result = ledger.verify(trusted={"researcher": public})
```

## Pinning the head: the honest limit of bare verification

A chain proves its own consistency — which means a *shortened* copy
of a ledger is also a consistent chain. If events are dropped from
the end of a file, what remains is a prefix of a valid history, and
**bare verification passes it**. No amount of re-walking the file
can change that; the file cannot know it used to be longer.

The detection is a pin. Pass `expected_head` — a dict with any of
`head_hash` (the last event's hash), `min_events` (a minimum event
count), and `checkpoint_root` (the latest checkpoint's Merkle root,
compared against the root verification *recomputes*, never the root
the file merely claims):

```python
result = axiomere.verify_file(
    "study.axmr",
    expected_head={"head_hash": "…", "min_events": 42,
                   "checkpoint_root": "…"},
)
```

A shortfall fails with `shortfall`, a wrong final hash with
`head-mismatch`, a wrong checkpoint root with `root-mismatch`. The
values to pin come from outside the file — your own records, or an
anchored checkpoint root (below). A verification routine that checks
ledgers it cares about should pin the head, or compare the
recomputed checkpoint root against an anchored one; a bare `ok` on
its own does not rule out truncation.

## Malformed files are verdicts, not exceptions

`verify_file` never raises because a file is malformed or unreadable:
it returns `ok=False` with a named `reason`, so a checking routine
can treat a corrupt file and a failed verification the same way —
as results. Opening a ledger for appends is a different act and
keeps the stricter behaviour: a ledger that fails verification
refuses to `open`, with the failure as the exception.

## What you write must be exactly storable

Appending is the mirror image of the same exactness. A payload value
that cannot be stored exactly — a non-finite float (`NaN`, positive
or negative infinity) or an integer outside the exactly
representable range — raises `ValueError` at append time and appends
nothing; the file is byte-identical afterwards. (Earlier versions of
the bindings silently stored `NaN` as null and rounded huge integers
through floating point; that is gone.) Integers up to
`2**64 - 1` and down to `-2**63` are stored and read back exactly,
and finite floats round-trip bit-for-bit.

## What verification does and does not establish

- Verification establishes that **this file is exactly the history
  its chain commits to** — nothing was quietly altered after the
  fact, no signature is missing where signatures are the norm, and
  every checkpoint root is the root of the events actually present.
- Signatures checked against embedded keys establish
  *self-consistency*. Checking them against a caller-supplied
  trusted-key map is what establishes *identity*.
- Verification alone does not protect against a sole-copy operator
  recomputing a chain from the very first event (from genesis). That
  is what **layer 5 — external anchoring** of Merkle checkpoint
  roots — is for: deposit the root where the operator does not
  control it (a DOI-minting repository, a timestamp authority, a
  transparency log), and tampering becomes evident to anyone.
  Anchoring only protects a reader who compares the anchored root
  against the root verification *recomputes* from the file in hand
  (or pins it via `expected_head`) — never against a root read out
  of the file itself, which a forger can copy as easily as the
  honest writer wrote it. The core produces the roots and receipt
  data; anchor transport belongs to the embedding system, and a
  deployment that skips anchoring must say so.
