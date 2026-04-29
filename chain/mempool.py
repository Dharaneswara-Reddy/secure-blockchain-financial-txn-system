"""
Transaction mempool (transaction pool).

The mempool holds unconfirmed transactions that are waiting to be included
in a block.  It operates as a FIFO queue with a configurable size cap.

Usage::

    pool = Mempool()
    tx_id = pool.add_transaction({"sender": "A", "receiver": "B", "amount": 1.0})
    txs   = pool.select_transactions(max_count=10)   # pick for next block
    pool.remove_transactions([tx["id"] for tx in txs])
"""

import time
import uuid
from collections import deque
from typing import Any

from wallet.config import configure_logging

logger = configure_logging(__name__)

_DEFAULT_MAX_SIZE: int = 1_000


class Mempool:
    """In-memory FIFO transaction pool.

    Args:
        max_size: Maximum number of unconfirmed transactions the pool will
            hold before rejecting new ones.  Defaults to 1 000.
    """

    def __init__(self, max_size: int = _DEFAULT_MAX_SIZE) -> None:
        self._transactions: deque[dict[str, Any]] = deque()
        self.max_size = max_size

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_transaction(self, tx: dict[str, Any]) -> str:
        """Add a transaction and return its generated UUID.

        Args:
            tx: Transaction dict.  Must contain at least ``sender``,
                ``receiver``, and ``amount``.

        Returns:
            UUID string assigned to this transaction.

        Raises:
            OverflowError: If the pool has reached *max_size*.
        """
        if len(self._transactions) >= self.max_size:
            raise OverflowError(f"Mempool is full (max {self.max_size} transactions)")

        tx_id = str(uuid.uuid4())
        entry: dict[str, Any] = {
            "id": tx_id,
            "submitted_at": time.time(),
            **tx,
        }
        self._transactions.append(entry)
        logger.debug("TX added to mempool: %s", tx_id)
        return tx_id

    def remove_transactions(self, tx_ids: list[str]) -> int:
        """Remove transactions by ID (e.g. after they are mined).

        Args:
            tx_ids: List of UUIDs to remove.

        Returns:
            Number of transactions actually removed.
        """
        id_set = set(tx_ids)
        before = len(self._transactions)
        self._transactions = deque(tx for tx in self._transactions if tx["id"] not in id_set)
        removed = before - len(self._transactions)
        logger.debug("Removed %d tx(s) from mempool", removed)
        return removed

    def clear(self) -> None:
        """Remove all pending transactions."""
        self._transactions.clear()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def select_transactions(self, max_count: int = 10) -> list[dict[str, Any]]:
        """Return up to *max_count* transactions (FIFO order, non-destructive)."""
        return list(self._transactions)[:max_count]

    def get_all(self) -> list[dict[str, Any]]:
        """Return a snapshot of all pending transactions."""
        return list(self._transactions)

    def pending_count(self) -> int:
        """Return the current number of pending transactions."""
        return len(self._transactions)

    def __len__(self) -> int:
        return len(self._transactions)
