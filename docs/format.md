# The `.axmr` format

A ledger is a **single file**, extension `.axmr`, deliberately
inspectable with generic tools:

```text
AXMR1
{"actor":…,"hash":…,"payload":…,"prev_hash":…,"seq":1,"sig":…,"signer":…,"ts":…,"type":…}
…
```

- **Line 1 is the magic `AXMR1`.** Verification rejects anything else.
- **One event per line, canonical JSON** — object keys sorted
  recursively, compact separators. Hashing is defined over this
  encoding, so independent implementations can verify each other's
  files byte-for-byte. The encoding is pinned in full below, and
  verification enforces it: a line that parses to the right event
  but is not spelled the canonical way fails verification.
- **Appends are fsync'd.**
- A future binary framing must preserve the same event model and hash
  definitions.

## The canonical encoding, pinned

These rules are the whole contract — an implementation that follows
them produces and verifies the same files as the reference:

- **Objects:** keys sorted lexicographically (byte order),
  recursively; compact separators — no whitespace anywhere.
- **Strings:** emitted as raw UTF-8. Only `"` (as `\"`), `\` (as
  `\\`), and the control characters U+0000–U+001F are escaped — the
  short escapes `\b \t \n \f \r` where JSON defines them, otherwise
  `\u00XX` with lowercase hex. Nothing else is escaped: non-ASCII
  characters (é, ☕, €) appear literally.
- **Numbers:** integers are exact, in plain decimal. Non-integers
  use the shortest decimal that round-trips to the same value, in
  plain form (`0.30000000000000004`, `1.0`, `-0.0`) or exponent form
  where the reference chooses it — the exponent always signed and
  never zero-padded (`1e-7`, `5e-324`, `1e+21`, never `1e-07`).
  Parsing must be correctly rounded (round-to-nearest-even), so a
  written decimal reads back as the identical value.
- **Event hash:** `SHA-256(prev_hash ‖ canonical(body))`, where
  `prev_hash` enters as its 64-character lowercase hex *text* (not
  raw bytes) and the body is the canonical encoding of
  `{seq, type, ts, actor, payload, prev_hash}`. The genesis event's
  `prev_hash` is 64 zeros.
- **Merkle root:** the leaves are event-hash hex strings; a parent
  is `SHA-256(left_hex ‖ right_hex)` over the hex text; an odd
  element is paired with itself; a single element is its own root;
  the empty set's root is `SHA-256("")`.
- **Snapshot id:** `SHA-256(canonical({"content": <content>,
  "parent": <parent-or-null>}))` — the canonical encoding of that
  two-key object, hashed.

## The event

Every event carries:

| Field | Meaning |
|---|---|
| `seq` | Position in the chain, from 1. |
| `prev_hash` | The previous event's hash (the genesis event points at the all-zero hash). |
| `hash` | `SHA-256(prev_hash ‖ canonical(event body))`. |
| `type` | The event kind (append, snapshot, dead, checkpoint, …). |
| `actor` | Who appended it. |
| `signer` / `sig` | The actor's Ed25519 public key and the signature over the event hash, for signed appends. |
| `ts` | Timestamp. |
| `payload` | The event body — for a snapshot, the record content. |

## Records are lineages

- A **record** is a lineage of **snapshots**.
- A **snapshot** is content-addressed: its id is the hash of its
  content and its parent's id, under the pinned construction above;
  the first snapshot's parent is null.
- **Revision** = a new snapshot. The old one is *superseded* and stays
  readable.
- **Withdrawal** = a new snapshot with `status: "dead"`, a mandatory
  `reason`, and `score: 0.0`. Status serves correct consumers; 0.0
  protects score-only consumers from continuing to use a dead record.
- **Score** (epistemic weight) and **status** (lifecycle) are separate
  fields and are never conflated.
- The **current view** is a fold — the events applied in order to
  produce it: latest snapshot per record, dead
  excluded by default. It is a projection; producing it never alters
  the log.

## Signing keys

Keys are Ed25519. `generate_keypair()` returns
`(seed_hex, public_key_hex)`; seeds are held by actors and are **never
written into the ledger**. The ledger stores public keys (embedded per
event) and signatures only. Key rotation is an application-level act:
new appends use the new key, old signatures verify against the keys
embedded in their events — history is not re-signed, ever.

## The erasure exception — specified, narrow, not implemented

Payloads are plaintext in v0.1. The design reserves exactly one
exception to append-only, for documented legal compulsion:
per-record payload encryption with an owner-signed **erasure
certificate** appended to the chain and destruction of that record's
key (the certificate, hashes, and signatures remain; the chain still
verifies). **It is not implemented in v0.1, has no API, and no
deployment may imply it exists until it does.** Ingest discipline is
the primary defense: secrets and personal data should be referenced
by hash, not embedded as payloads.

## Non-goals (v0.1)

No query language, no secondary indexes, no networking/server mode,
no multi-writer concurrency (a ledger has one sequencing writer;
concurrent appends are serialized by the owning process), no
compression. These are later layers built *around* the append-only
core, never inside it.
