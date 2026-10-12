"""Axiomere — a truth ledger, from Python.

An append-only, signed, hash-chained record store. Records change only
by appending new *snapshots*; nothing is ever updated in place and
nothing is ever deleted. Withdrawal is a snapshot marked ``dead`` with
a reason on the record and its score set to 0.0.

    >>> import axiomere
    >>> ledger = axiomere.Database.create("study.axmr")
    >>> ledger.snapshot("claim-1", {"text": "X holds", "score": 0.8},
    ...                 actor="researcher", score=0.8)
    >>> ledger.snapshot("claim-1", {"text": "X holds, narrowed"},
    ...                 actor="researcher", score=0.6)   # supersedes
    >>> ledger.dead("claim-1", reason="retracted", actor="adjudicator")
    >>> ledger.verify()["ok"]
    True

The native core is Rust (github.com/AXIOVEX/axiomere); this package
wraps its PyO3 extension module ``_axiomere``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

try:
    import _axiomere
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "axiomere requires its native extension, which is built from the "
        "AXIOVEX/axiomere repository:  pip install maturin && "
        "git clone https://github.com/AXIOVEX/axiomere && "
        "maturin develop -m axiomere/crates/axiomere-py/Cargo.toml"
    ) from exc

__version__ = "0.1.0"
__all__ = ["Database", "Verification", "generate_keypair", "verify_file"]


@dataclass(frozen=True)
class Verification:
    ok: bool
    events: int
    break_seq: Optional[int]
    reason: Optional[str]
    signatures_checked: int
    signatures_failed: int


class Database:
    """An Axiomere ledger file (``*.axmr``).

    Note what is *not* here: there is no update and no delete, in this
    API or in the core beneath it. Change happens by appending
    snapshots; withdrawal is :meth:`dead`.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    # -- construction ---------------------------------------------------

    @classmethod
    def create(cls, path: str, *, seed_hex: Optional[str] = None) -> "Database":
        if seed_hex:
            return cls(_axiomere.create_with_seed(path, seed_hex))
        return cls(_axiomere.PyLedger.create(path))

    @classmethod
    def open(cls, path: str, *, seed_hex: Optional[str] = None) -> "Database":
        """Open an existing ledger. A ledger that fails verification
        refuses to open for appends — a broken record is evidence,
        never a writing surface."""
        if seed_hex:
            return cls(_axiomere.open_with_seed(path, seed_hex))
        return cls(_axiomere.PyLedger.open(path))

    # -- appends (the only writes that exist) ------------------------------

    def append(self, event_type: str, payload: Any, *, actor: str) -> dict:
        return json.loads(self._inner.append(event_type, payload, actor))

    def snapshot(
        self,
        record_id: str,
        content: Any,
        *,
        actor: str,
        score: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> dict:
        """Append a new snapshot of a record, superseding its latest."""
        return json.loads(
            self._inner.snapshot(record_id, content, actor, "live", score, reason)
        )

    def dead(self, record_id: str, *, reason: str, actor: str) -> dict:
        """Withdraw a record the only way Axiomere allows: a new
        snapshot, status ``dead``, the reason on the record, score
        forced to 0.0. Its full history remains readable."""
        return json.loads(self._inner.mark_dead(record_id, reason, actor))

    def checkpoint(self, *, actor: str) -> dict:
        """Close the current range under a signed Merkle checkpoint."""
        return json.loads(self._inner.checkpoint(actor))

    # -- reads ------------------------------------------------------------

    def current(self, *, include_dead: bool = False) -> dict:
        """Latest snapshot per record. Dead records are excluded
        unless ``include_dead`` — audit views ask for them explicitly."""
        return self._inner.current_view(include_dead)

    def events(self) -> list:
        return self._inner.events()

    def verify(self) -> Verification:
        v = self._inner.verify()
        return Verification(
            ok=v["ok"],
            events=v["events"],
            break_seq=v["break_seq"],
            reason=v["reason"],
            signatures_checked=v["signatures_checked"],
            signatures_failed=v["signatures_failed"],
        )


def generate_keypair() -> tuple[str, str]:
    """Return ``(seed_hex, public_key_hex)`` for a new Ed25519 actor key.
    Keep the seed out of the ledger — and out of source control."""
    return _axiomere.generate_keypair()


def verify_file(path: str) -> tuple[bool, int, Optional[str]]:
    """Verify a ledger file standalone: ``(ok, event_count, reason)``."""
    return _axiomere.verify_file(path)
