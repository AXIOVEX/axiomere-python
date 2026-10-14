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
    >>> ledger.verify().ok
    True

The native core is Rust (github.com/AXIOVEX/axiomere); this package
wraps its PyO3 extension module ``_axiomere``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional

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
    """The full result of verifying a ledger — the same eight fields
    on every surface (this package, the standalone file check, the
    core's CLI).

    ``unsigned_events`` names the sequence numbers of events that
    carry no signature; it is reported in every mode, so an unsigned
    ledger is a visible state, never a silent one. ``untrusted_actors``
    names actors a trusted-key check refused to vouch for (see
    :meth:`Database.verify`)."""

    ok: bool
    events: int
    break_seq: Optional[int]
    reason: Optional[str]
    signatures_checked: int
    signatures_failed: int
    unsigned_events: tuple[int, ...] = ()
    untrusted_actors: tuple[str, ...] = ()


def _to_verification(result: dict) -> Verification:
    return Verification(
        ok=result["ok"],
        events=result["events"],
        break_seq=result["break_seq"],
        reason=result["reason"],
        signatures_checked=result["signatures_checked"],
        signatures_failed=result["signatures_failed"],
        unsigned_events=tuple(result["unsigned_events"]),
        untrusted_actors=tuple(result["untrusted_actors"]),
    )


def _policy_args(
    trusted: Optional[Mapping[str, str]],
    expected_head: Optional[Mapping[str, Any]],
) -> tuple[Optional[dict], Optional[dict]]:
    # Copy into plain dicts for the extension. ``None`` is preserved
    # exactly: it means something different from an empty dict (see
    # Database.verify), so it must not be normalised into one.
    return (
        dict(trusted) if trusted is not None else None,
        dict(expected_head) if expected_head is not None else None,
    )


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
        """Append one event. Payload values must be exactly storable:
        a non-finite float (NaN, infinity) or an integer outside the
        exactly representable range raises ``ValueError`` and appends
        nothing — values are never silently rounded or turned into
        null on the way in."""
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

    def verify(
        self,
        *,
        trusted: Optional[Mapping[str, str]] = None,
        expected_head: Optional[Mapping[str, Any]] = None,
    ) -> Verification:
        """Verify this ledger and return the full :class:`Verification`.

        ``trusted`` selects the signature policy:

        - ``None`` (the default) is *bare* mode: signatures are
          checked against the public keys embedded in the events
          themselves. That establishes the file is exactly the history
          its chain commits to — self-consistency. It does not
          establish *who* wrote it: a key proves itself.
        - A dict of ``{actor: public_key_hex}`` is *trusted* mode —
          the identity check. Every event's actor must appear in the
          map, and every event must be signed with that actor's mapped
          key. An event by an actor the map does not name fails
          verification and the actor is reported in
          ``untrusted_actors``; there is no fallback to the key
          embedded in the event. An empty dict is a real choice with
          its own meaning — it trusts nobody, so every event fails —
          and is *not* the same as ``None``.

        ``expected_head`` pins what the end of the ledger must look
        like, as a dict with any of the keys ``head_hash`` (the last
        event's hash), ``min_events`` (a minimum event count), and
        ``checkpoint_root`` (the latest checkpoint's Merkle root,
        compared against the root verification recomputes, never the
        root the file merely claims). A shortened copy of a ledger —
        events dropped from the end — is still a perfectly valid chain
        on its own, so bare verification passes it; the pin is what
        catches the shortfall.
        """
        trusted_arg, head_arg = _policy_args(trusted, expected_head)
        return _to_verification(
            self._inner.verify(trusted=trusted_arg, expected_head=head_arg)
        )


def generate_keypair() -> tuple[str, str]:
    """Return ``(seed_hex, public_key_hex)`` for a new Ed25519 actor key.
    Keep the seed out of the ledger — and out of source control."""
    return _axiomere.generate_keypair()


def verify_file(
    path: str,
    *,
    trusted: Optional[Mapping[str, str]] = None,
    expected_head: Optional[Mapping[str, Any]] = None,
) -> Verification:
    """Verify a ledger file standalone — no :class:`Database` needed —
    and return the full :class:`Verification`, the same result
    :meth:`Database.verify` gives.

    A malformed or unreadable file is a verdict, not an exception:
    this returns ``ok=False`` with a named ``reason`` instead of
    raising. (Opening a ledger for appends is different — that gate
    keeps raising, by design.) ``trusted`` and ``expected_head`` mean
    exactly what they mean on :meth:`Database.verify`.
    """
    trusted_arg, head_arg = _policy_args(trusted, expected_head)
    return _to_verification(
        _axiomere.verify_file(path, trusted=trusted_arg, expected_head=head_arg)
    )
