"""Regression: the verification policy, at the Python surface.

Companion to AXIOVEX/axiomere Spec 003 (verification policy). The core
spec's defect class, demonstrated by the 2026-10-13 red team, was that
v0.1.0 verification validated only what is *present*: a forged ledger
carrying a transplanted checkpoint root passed, stripped signatures
passed, an unmapped actor passed identity mode, and a truncated
ledger passed — while the Python surface could not even express the
identity check. These tests mirror the core's acceptance from Python:

- an honest signed ledger verifies bare and in trusted mode;
- a checkpoint root transplanted from another ledger fails
  (``checkpoint-root-mismatch``), even re-signed by its true author;
- stripped signatures fail trusted mode, fail bare mode when any
  signature material remains, and are always *reported* in
  ``unsigned_events`` — never silent;
- an actor missing from the trusted map fails with the actor named
  in ``untrusted_actors`` (the F-VP-5 check, from Python);
- a truncated ledger passes bare verification — a prefix of a valid
  chain is a valid chain — and fails under an expected-head pin;
- NaN / infinity / out-of-range integers raise ``ValueError`` at
  append time and append nothing (the F-VP-8 battery), while the
  exact-integer boundary values round-trip exactly;
- ``verify_file`` reports malformed files as verdicts, never raises.

The file surgery below (re-hashing, re-signing, stripping) rebuilds
the red team's constructions from Python alone: canonical JSON per
the pinned encoding, SHA-256 over ``prev_hash || canonical(body)``,
and a small pure-Python Ed25519 signer (RFC 8032) for the attacker's
key. Its correctness is not assumed — a control re-signs an untouched
event and the ledger must still verify.
"""

import hashlib
import json
import struct

import pytest

import axiomere


# ---------------------------------------------------------------------------
# Pure-Python Ed25519 (RFC 8032 reference), used only to re-sign forged
# lines with the attacker's own key, exactly as the red team did.

_Q = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493


def _inv(x):
    return pow(x, _Q - 2, _Q)


_D = -121665 * _inv(121666) % _Q
_I = pow(2, (_Q - 1) // 4, _Q)


def _xrecover(y):
    xx = (y * y - 1) * _inv(_D * y * y + 1)
    x = pow(xx, (_Q + 3) // 8, _Q)
    if (x * x - xx) % _Q != 0:
        x = (x * _I) % _Q
    if x % 2 != 0:
        x = _Q - x
    return x


_BY = 4 * _inv(5) % _Q
_B = [_xrecover(_BY) % _Q, _BY]


def _edwards(P, Q):
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + _D * x1 * x2 * y1 * y2)
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - _D * x1 * x2 * y1 * y2)
    return [x3 % _Q, y3 % _Q]


def _scalarmult(P, e):
    if e == 0:
        return [0, 1]
    Q = _scalarmult(P, e // 2)
    Q = _edwards(Q, Q)
    if e & 1:
        Q = _edwards(Q, P)
    return Q


def _encodeint(y):
    bits = [(y >> i) & 1 for i in range(256)]
    return bytes(sum(bits[i * 8 + j] << j for j in range(8)) for i in range(32))


def _encodepoint(P):
    x, y = P
    bits = [(y >> i) & 1 for i in range(255)] + [x & 1]
    return bytes(sum(bits[i * 8 + j] << j for j in range(8)) for i in range(32))


def _bit(h, i):
    return (h[i // 8] >> (i % 8)) & 1


def _secret_scalar(h):
    return 2**254 + sum(2**i * _bit(h, i) for i in range(3, 254))


def ed25519_publickey(seed: bytes) -> bytes:
    a = _secret_scalar(hashlib.sha512(seed).digest())
    return _encodepoint(_scalarmult(_B, a))


def ed25519_sign(seed: bytes, msg: bytes) -> bytes:
    h = hashlib.sha512(seed).digest()
    a = _secret_scalar(h)
    pub = _encodepoint(_scalarmult(_B, a))

    def hint(m):
        digest = hashlib.sha512(m).digest()
        return sum(2**i * _bit(digest, i) for i in range(512))

    r = hint(h[32:64] + msg)
    R = _scalarmult(_B, r)
    S = (r + hint(_encodepoint(R) + pub + msg) * a) % _L
    return _encodepoint(R) + _encodeint(S)


# ---------------------------------------------------------------------------
# Ledger-file surgery helpers. Canonical JSON per the pinned encoding
# (keys sorted recursively, compact separators, raw UTF-8). Fixtures
# edited this way carry only int/str payloads, whose canonical forms
# Python and the writer agree on byte-for-byte.


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _read_events(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "AXMR1"
    return [json.loads(line) for line in lines[1:] if line]


def _write_events(path, events):
    path.write_text(
        "AXMR1\n" + "".join(_canon(ev) + "\n" for ev in events), encoding="utf-8"
    )


def _resign(ev, seed: bytes):
    """Recompute an event's hash over its (possibly edited) body and
    re-sign it with the given seed — the attacker's full capability
    over their own forged history."""
    body = {
        "seq": ev["seq"],
        "type": ev["type"],
        "ts": ev["ts"],
        "actor": ev["actor"],
        "payload": ev["payload"],
        "prev_hash": ev["prev_hash"],
    }
    ev["hash"] = hashlib.sha256(
        (ev["prev_hash"] + _canon(body)).encode("utf-8")
    ).hexdigest()
    ev["signer"] = ed25519_publickey(seed).hex()
    ev["sig"] = ed25519_sign(seed, ev["hash"].encode("utf-8")).hex()
    return ev


def _signed_db(path, actor="alice", notes=("alpha", "beta")):
    seed, pk = axiomere.generate_keypair()
    db = axiomere.Database.create(str(path), seed_hex=seed)
    for i, text in enumerate(notes):
        db.append("note", {"n": i + 1, "text": text}, actor=actor)
    return db, seed, pk


# ---------------------------------------------------------------------------
# Honest ledgers, both modes


def test_honest_ledger_verifies_bare_and_trusted(tmp_path):
    p = tmp_path / "t.axmr"
    seed, pk = axiomere.generate_keypair()
    db = axiomere.Database.create(str(p), seed_hex=seed)
    db.snapshot("rec-1", {"claim": "X holds"}, actor="alice", score=0.8)
    db.snapshot("rec-1", {"claim": "X holds, narrowed"}, actor="alice", score=0.6)
    db.checkpoint(actor="alice")

    v = db.verify()
    assert v.ok and v.events == 3
    assert v.signatures_checked == 3 and v.signatures_failed == 0
    assert v.unsigned_events == () and v.untrusted_actors == ()
    assert v.break_seq is None and v.reason is None

    vt = db.verify(trusted={"alice": pk})
    assert vt.ok and vt.signatures_checked == 3

    # The standalone surface returns the identical result object.
    assert axiomere.verify_file(str(p), trusted={"alice": pk}) == vt
    assert axiomere.verify_file(str(p)) == v


def test_trusted_mode_rejects_the_wrong_key(tmp_path):
    p = tmp_path / "t.axmr"
    db, _seed, _pk = _signed_db(p)
    _other_seed, other_pk = axiomere.generate_keypair()
    v = db.verify(trusted={"alice": other_pk})
    assert not v.ok and v.reason == "signer-key-mismatch"
    assert v.signatures_failed == 1


# ---------------------------------------------------------------------------
# F-VP-5 from Python: an actor the map does not name is reported


def test_unmapped_actor_is_reported_untrusted(tmp_path):
    p = tmp_path / "t.axmr"
    db, _aseed, alice_pk = _signed_db(p, notes=("alpha",))
    mseed, _mpk = axiomere.generate_keypair()
    attacker = axiomere.Database.open(str(p), seed_hex=mseed)
    attacker.append("note", {"n": 99, "text": "mallory was here"}, actor="mallory")

    # Bare mode has no opinion about identity: mallory's events are
    # honestly signed, and the chain is intact.
    assert axiomere.verify_file(str(p)).ok

    for v in (
        axiomere.verify_file(str(p), trusted={"alice": alice_pk}),
        axiomere.Database.open(str(p)).verify(trusted={"alice": alice_pk}),
    ):
        assert not v.ok and v.reason == "untrusted-actor"
        assert v.untrusted_actors == ("mallory",)
        assert v.break_seq == 2

    # An empty map is not "no map": it trusts nobody, so the very
    # first (honest) actor is already untrusted.
    v = axiomere.verify_file(str(p), trusted={})
    assert not v.ok and v.reason == "untrusted-actor"
    assert v.untrusted_actors == ("alice",)


# ---------------------------------------------------------------------------
# Signature presence: stripping is caught, and always reported


def _stripped(path, seqs):
    events = _read_events(path)
    for ev in events:
        if ev["seq"] in seqs:
            ev.pop("sig", None)
            ev.pop("signer", None)
    _write_events(path, events)


def test_partially_stripped_ledger_fails_every_mode(tmp_path):
    p = tmp_path / "t.axmr"
    _db, _seed, pk = _signed_db(p, notes=("a", "b", "c"))
    _stripped(p, {2})
    for v in (
        axiomere.verify_file(str(p)),
        axiomere.verify_file(str(p), trusted={"alice": pk}),
    ):
        assert not v.ok and v.reason == "unsigned-event"
        assert v.break_seq == 2 and v.unsigned_events == (2,)


def test_fully_stripped_ledger_is_a_visible_state_not_a_silent_one(tmp_path):
    p = tmp_path / "t.axmr"
    _db, _seed, pk = _signed_db(p, notes=("a", "b", "c"))
    _stripped(p, {1, 2, 3})

    # Nothing in the file claims a signature any more, so bare mode
    # treats it as an honestly unsigned ledger — but the state is on
    # the face of the result, not passed over in silence.
    v = axiomere.verify_file(str(p))
    assert v.ok and v.signatures_checked == 0
    assert v.unsigned_events == (1, 2, 3)

    # Trusted mode is where the downgrade dies: alice is named, but
    # her events carry no signature to check against her key.
    v = axiomere.verify_file(str(p), trusted={"alice": pk})
    assert not v.ok and v.reason == "unsigned-event"
    assert v.unsigned_events == (1, 2, 3)


# ---------------------------------------------------------------------------
# RTB-01 from Python: the transplanted checkpoint root


def test_transplanted_checkpoint_root_fails(tmp_path):
    # The victim: an honest signed ledger with one checkpoint. Its
    # root is the value an external anchor would publish.
    vp = tmp_path / "victim.axmr"
    vdb, _vseed, _vpk = _signed_db(vp, notes=("the true history",))
    vdb.checkpoint(actor="alice")
    victim_root = _read_events(vp)[-1]["payload"]["merkle_root"]

    # The attacker: a different history, honestly signed with their
    # own key, closed by their own checkpoint.
    ap = tmp_path / "forged.axmr"
    adb, aseed, apk = _signed_db(ap, actor="mallory", notes=("forged", "history"))
    adb.checkpoint(actor="mallory")
    assert axiomere.verify_file(str(ap)).ok
    events = _read_events(ap)
    checkpoint_seq = events[-1]["seq"]
    assert events[-1]["payload"]["merkle_root"] != victim_root

    # Control: re-hash and re-sign the untouched checkpoint with the
    # attacker's key (pure-Python Ed25519). If the surgery harness
    # were unsound, this alone would break the file.
    seed_bytes = bytes.fromhex(aseed)
    assert ed25519_publickey(seed_bytes).hex() == apk
    _write_events(ap, events[:-1] + [_resign(dict(events[-1]), seed_bytes)])
    assert axiomere.verify_file(str(ap)).ok

    # The attack: transplant the victim's anchored root into the
    # forged checkpoint, re-hash, re-sign. Every signature is genuine
    # and the chain is intact — the root is simply not the root of
    # *this* history, and recomputation is what catches it.
    forged = dict(events[-1])
    forged["payload"] = dict(forged["payload"], merkle_root=victim_root)
    _write_events(ap, events[:-1] + [_resign(forged, seed_bytes)])
    for v in (
        axiomere.verify_file(str(ap)),
        axiomere.verify_file(str(ap), trusted={"mallory": apk}),
    ):
        assert not v.ok and v.reason == "checkpoint-root-mismatch"
        assert v.break_seq == checkpoint_seq


# ---------------------------------------------------------------------------
# Expected head: the only truncation detection


def test_truncation_passes_bare_and_fails_under_expected_head(tmp_path):
    p = tmp_path / "t.axmr"
    db, _seed, _pk = _signed_db(p, notes=("a", "b"))
    db.checkpoint(actor="alice")
    events = _read_events(p)
    head_hash = events[-1]["hash"]
    root = events[-1]["payload"]["merkle_root"]
    pin = {"head_hash": head_hash, "min_events": 3, "checkpoint_root": root}

    # The intact ledger passes under its own pin, on both surfaces.
    assert axiomere.verify_file(str(p), expected_head=pin).ok
    assert db.verify(expected_head=pin).ok

    # Drop the checkpoint (the last event). What remains is a valid
    # chain — bare verification says so, and the docs say it plainly.
    tp = tmp_path / "truncated.axmr"
    _write_events(tp, events[:-1])
    v = axiomere.verify_file(str(tp))
    assert v.ok and v.events == 2

    v = axiomere.verify_file(str(tp), expected_head={"min_events": 3})
    assert not v.ok and v.reason == "shortfall"
    v = axiomere.verify_file(str(tp), expected_head={"head_hash": head_hash})
    assert not v.ok and v.reason == "head-mismatch"
    v = axiomere.verify_file(str(tp), expected_head={"checkpoint_root": root})
    assert not v.ok and v.reason == "root-mismatch"


# ---------------------------------------------------------------------------
# F-VP-8 from Python: values that cannot be stored exactly are errors


def test_nonfinite_and_out_of_range_values_raise_and_append_nothing(tmp_path):
    p = tmp_path / "t.axmr"
    db = axiomere.Database.create(str(p))
    db.append("note", {"v": 1}, actor="alice")
    before = p.read_bytes()

    for bad in (float("nan"), float("inf"), float("-inf"), 2**70, -(2**70)):
        with pytest.raises(ValueError):
            db.append("note", {"v": bad}, actor="alice")
        assert p.read_bytes() == before

    with pytest.raises(ValueError):
        db.snapshot("rec", {"v": float("nan")}, actor="alice")
    assert p.read_bytes() == before


def test_exact_integer_boundaries_and_floats_round_trip(tmp_path):
    p = tmp_path / "t.axmr"
    db = axiomere.Database.create(str(p))
    for value in (2**64 - 1, 2**63, -(2**63)):
        db.append("note", {"v": value}, actor="alice")
    db.append("note", {"v": 0.30000000000000004}, actor="alice")

    got = [ev["payload"]["v"] for ev in db.events()]
    assert got[:3] == [2**64 - 1, 2**63, -(2**63)]
    assert all(isinstance(v, int) for v in got[:3])
    assert struct.pack(">d", got[3]) == struct.pack(">d", 0.30000000000000004)
    assert db.verify().ok


# ---------------------------------------------------------------------------
# verify_file reports malformed files; it does not raise on them


def test_verify_file_reports_malformed_files_instead_of_raising(tmp_path):
    garbage = tmp_path / "garbage.axmr"
    garbage.write_text("this is not a ledger\n", encoding="utf-8")
    v = axiomere.verify_file(str(garbage))
    assert isinstance(v, axiomere.Verification)
    assert not v.ok and v.reason

    empty = tmp_path / "empty.axmr"
    empty.write_text("", encoding="utf-8")
    v = axiomere.verify_file(str(empty))
    assert not v.ok and v.reason

    broken = tmp_path / "broken.axmr"
    broken.write_text("AXMR1\n{not json\n", encoding="utf-8")
    v = axiomere.verify_file(str(broken))
    assert not v.ok and v.reason

    v = axiomere.verify_file(str(tmp_path / "does-not-exist.axmr"))
    assert not v.ok and v.reason
