"""Regression: float payloads written by this package verify on reopen.

Companion to AXIOVEX/axiomere Spec 002 (float canonicalization). The
core's reader once parsed decimals needing >= 17 significant digits
1 ULP high (serde_json without the ``float_roundtrip`` feature), so an
untampered log written through this wrapper failed hash verification
on reopen — the failure Tekmerion's platform ledger hit downstream
with a high-precision timestamp float. These tests pin the exact
downstream reproduction plus a sweep of the characterized trigger
class against the real extension, so the defect cannot silently
return on this side. On a pre-fix core build, every test here fails:
``Database.open`` raises ``verification failed at seq 1:
hash-mismatch`` and in-session ``verify()`` already reports false.
"""

import struct

import axiomere

REPRODUCTION = {"ts_like": 1791810119.6349843, "plain": 0.5}

# Finite floats whose shortest decimal form needs >= 17 significant
# digits (the trigger class), plus boundary shapes from the core
# spec's characterization matrix.
TRIGGER_FLOATS = [
    1791810119.6349843,  # the downstream reproduction value
    -1791810119.6349843,  # negative twin
    1.0086398161248257e149,  # exponent form, 17 significant digits
    0.30000000000000004,  # 0.1 + 0.2 — 17 significant digits
    123456789.12345679,  # 17 significant digits, plain form
    2.2250738585072014e-308,  # smallest normal
    1.7976931348623157e308,  # largest finite
    5e-324,  # smallest subnormal
    1.0,  # integral-valued float
    -0.0,  # signed zero
]


def _bits(x: float) -> bytes:
    return struct.pack("<d", x)


def test_reproduction_payload_verifies_on_reopen(tmp_path):
    p = str(tmp_path / "t.axmr")
    db = axiomere.Database.create(p)
    db.snapshot("reading", dict(REPRODUCTION), actor="alice")
    assert db.verify().ok

    reopened = axiomere.Database.open(p)  # must not refuse a sound log
    v = reopened.verify()
    assert v.ok and v.events == 1

    ok, count, reason = axiomere.verify_file(p)
    assert ok and count == 1 and reason is None

    content = reopened.current()["reading"]["content"]
    assert _bits(content["ts_like"]) == _bits(REPRODUCTION["ts_like"])
    assert _bits(content["plain"]) == _bits(REPRODUCTION["plain"])


def test_trigger_float_sweep_verifies_on_reopen(tmp_path):
    p = str(tmp_path / "t.axmr")
    payload = {f"v{i}": x for i, x in enumerate(TRIGGER_FLOATS)}
    db = axiomere.Database.create(p)
    db.snapshot("sweep", payload, actor="alice")
    assert db.verify().ok

    reopened = axiomere.Database.open(p)
    v = reopened.verify()
    assert v.ok and v.events == 1

    ok, count, reason = axiomere.verify_file(p)
    assert ok and count == 1 and reason is None

    content = reopened.current()["sweep"]["content"]
    for key, original in payload.items():
        assert _bits(content[key]) == _bits(original), key

    # A repaired-path log stays appendable after reopen.
    reopened.snapshot("after", {"ok": True}, actor="alice")
    assert reopened.verify().ok
