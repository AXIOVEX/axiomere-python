# Python API

The package exports four names: `Database`, `Verification`,
`generate_keypair`, and `verify_file`.

```python
import axiomere
```

## Keys

```python
seed, public = axiomere.generate_keypair()
```

Returns `(seed_hex, public_key_hex)` for a new Ed25519 actor key.
Keep the seed out of the ledger — and out of source control.

## Opening a ledger

```python
ledger = axiomere.Database.create("study.axmr")                    # fresh ledger
ledger = axiomere.Database.create("study.axmr", seed_hex=seed)     # signed appends
ledger = axiomere.Database.open("study.axmr")                      # existing ledger
ledger = axiomere.Database.open("study.axmr", seed_hex=seed)
```

`open` verifies the ledger first: **a ledger that fails verification
refuses to open for appends** — a broken record is evidence, never a
writing surface.

## Appends — the only writes that exist

```python
ledger.append("note", {"text": "…"}, actor="researcher")           # raw event
ledger.snapshot("claim-1", {"text": "X holds"}, actor="researcher", score=0.8)
ledger.snapshot("claim-1", {"text": "X holds, narrowed"}, actor="researcher", score=0.6)
ledger.dead("claim-1", reason="retracted", actor="adjudicator")
ledger.checkpoint(actor="researcher")
```

- `append(event_type, payload, *, actor)` — append a raw event;
  returns the event as a dict.
- `snapshot(record_id, content, *, actor, score=None, reason=None)` —
  append a new snapshot of a record, superseding its latest.
- `dead(record_id, *, reason, actor)` — withdraw a record the only
  way Axiomere allows: a new snapshot, status `dead`, the reason on
  the record, score forced to 0.0. Its full history remains readable.
- `checkpoint(*, actor)` — close the current range under a signed
  Merkle checkpoint.

## Reads

```python
ledger.current()                    # latest snapshot per record; dead excluded
ledger.current(include_dead=True)   # audit view: dead records included, explicitly
ledger.events()                     # the full event list
```

## Verification

```python
result = ledger.verify()
# Verification(ok=True, events=3, break_seq=None, reason=None,
#              signatures_checked=3, signatures_failed=0)

ok, count, reason = axiomere.verify_file("study.axmr")   # standalone, no Database needed
```

`Verification` is a frozen dataclass (an immutable result object):
`ok`, `events`, `break_seq`
(the sequence number where the chain breaks, if it does), `reason`,
`signatures_checked`, `signatures_failed`. See
[Verification](verification.md) for what is checked and what a
failure means.

## What is not here

There is no `update`, no `delete`, no `remove`, no `redact` — not
public, not private, not behind a flag, in this API or in the core
beneath it. Change happens by appending snapshots; withdrawal is
`dead`. See [the format](format.md) for the one erasure exception the
design reserves — specified, narrow, and **not implemented** in v0.1.
