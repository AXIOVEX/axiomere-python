import axiomere


def test_snapshot_lineage_and_view(tmp_path):
    db = axiomere.Database.create(str(tmp_path / "t.axmr"))
    db.snapshot("rec-1", {"claim": "X holds"}, actor="alice", score=0.8)
    db.snapshot("rec-1", {"claim": "X holds, revised"}, actor="alice", score=0.6)
    view = db.current()
    assert view["rec-1"]["content"]["claim"] == "X holds, revised"
    assert view["rec-1"]["parent"] is not None
    v = db.verify()
    assert v.ok and v.events == 2


def test_dead_semantics(tmp_path):
    db = axiomere.Database.create(str(tmp_path / "t.axmr"))
    db.snapshot("rec-2", {"claim": "Y"}, actor="bob", score=0.3)
    db.dead("rec-2", reason="retracted", actor="alice")
    assert "rec-2" not in db.current()
    audit = db.current(include_dead=True)
    assert audit["rec-2"]["status"] == "dead"
    assert audit["rec-2"]["score"] == 0.0
    assert audit["rec-2"]["reason"] == "retracted"
    # history is complete: both snapshots still readable as events
    assert len(db.events()) == 2
    assert db.verify().ok


def test_signed_appends_verify(tmp_path):
    seed, _pk = axiomere.generate_keypair()
    db = axiomere.Database.create(str(tmp_path / "t.axmr"), seed_hex=seed)
    db.snapshot("r", {"a": 1}, actor="alice")
    v = db.verify()
    assert v.ok and v.signatures_checked == 1 and v.signatures_failed == 0


def test_tampered_file_fails_verify_file(tmp_path):
    p = tmp_path / "t.axmr"
    db = axiomere.Database.create(str(p))
    db.snapshot("r", {"claim": "original"}, actor="alice")
    text = p.read_text().replace("original", "FORGED!!")
    p.write_text(text)
    ok, count, reason = axiomere.verify_file(str(p))
    assert not ok and reason == "hash-mismatch" and count == 1


def test_broken_log_refuses_to_open(tmp_path):
    p = tmp_path / "t.axmr"
    db = axiomere.Database.create(str(p))
    db.snapshot("r", {"claim": "original"}, actor="alice")
    p.write_text(p.read_text().replace("original", "FORGED!!"))
    try:
        axiomere.Database.open(str(p))
        raise AssertionError("expected open to refuse a broken log")
    except ValueError:
        pass
