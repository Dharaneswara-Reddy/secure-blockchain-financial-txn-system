"""
Block data structure with SHA-256 hashing.

Each block contains:
  - index       : position in the chain (0 = genesis)
  - timestamp   : Unix time of block creation
  - transactions: list of transaction dicts included in this block
  - previous_hash: SHA-256 hash of the preceding block (links the chain)
  - nonce       : integer adjusted during Proof-of-Work mining
  - hash        : SHA-256 digest of all the above fields (computed on init)

Security notes:
  - Fields are serialised with sorted keys (canonical JSON) so the hash
    is deterministic regardless of dict insertion order.
  - `compute_hash` always re-derives from the canonical representation;
    callers must call it explicitly after mutating `nonce` during mining.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

GENESIS_PREV_HASH: str = "0" * 64


def _sha256(data: str) -> str:
    """Return the hex-encoded SHA-256 digest of *data*."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


@dataclass
class Block:
    """A single block in the blockchain."""

    index: int
    transactions: list[dict[str, Any]]
    previous_hash: str
    timestamp: float = field(default_factory=time.time)
    nonce: int = 0
    hash: str = field(default="", init=True)

    def __post_init__(self) -> None:
        if not self.hash:
            self.hash = self.compute_hash()

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    def compute_hash(self) -> str:
        """Return the SHA-256 hash of this block's canonical representation.

        The hash covers: index, timestamp, transactions, previous_hash, nonce.
        Keys are sorted to guarantee determinism.
        """
        payload = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        return _sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")))

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict representation of this block."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
            "tx_count": len(self.transactions),
        }
