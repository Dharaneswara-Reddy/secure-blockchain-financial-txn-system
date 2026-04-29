"""
Blockchain — links blocks into an immutable chain.

The Blockchain manages:
  - Genesis block creation (index 0, hardcoded previous_hash of 64 zeros)
  - Adding pre-mined blocks with full validation
  - Chain integrity verification (hash + linkage checks)
  - An embedded Mempool for pending transactions

Usage::

    bc = Blockchain()
    # ... mine a block externally ...
    bc.add_block(mined_block)
    assert bc.is_valid_chain()
"""

from chain.block import GENESIS_PREV_HASH, Block
from chain.mempool import Mempool
from wallet.config import configure_logging

logger = configure_logging(__name__)


class Blockchain:
    """Manages the ordered sequence of blocks and the transaction mempool.

    Args:
        genesis_timestamp: Fixed timestamp for the genesis block.  Pass 0.0
            in tests to get a deterministic genesis hash.
    """

    def __init__(self, genesis_timestamp: float = 0.0) -> None:
        self.chain: list[Block] = []
        self.mempool: Mempool = Mempool()
        self._create_genesis_block(genesis_timestamp)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_genesis_block(self, timestamp: float) -> None:
        genesis = Block(
            index=0,
            transactions=[],
            previous_hash=GENESIS_PREV_HASH,
            timestamp=timestamp,
            nonce=0,
        )
        self.chain.append(genesis)
        logger.info("Genesis block created — hash: %s", genesis.hash)

    # ------------------------------------------------------------------
    # Chain access
    # ------------------------------------------------------------------

    def last_block(self) -> Block:
        """Return the most recently added block."""
        return self.chain[-1]

    def height(self) -> int:
        """Return the number of blocks in the chain (including genesis)."""
        return len(self.chain)

    def total_transactions(self) -> int:
        """Return the sum of transactions across all blocks."""
        return sum(len(b.transactions) for b in self.chain)

    # ------------------------------------------------------------------
    # Block addition
    # ------------------------------------------------------------------

    def add_block(self, block: Block) -> bool:
        """Append *block* to the chain after validation.

        Validation checks:
          1. ``block.previous_hash`` must equal the current last block's hash.
          2. ``block.hash`` must equal ``block.compute_hash()``.

        Args:
            block: A fully mined Block (nonce and hash already set).

        Returns:
            ``True`` if the block was accepted, ``False`` otherwise.
        """
        if block.previous_hash != self.last_block().hash:
            logger.warning(
                "Block #%d rejected — previous_hash mismatch (expected %s, got %s)",
                block.index,
                self.last_block().hash[:12],
                block.previous_hash[:12],
            )
            return False

        if block.hash != block.compute_hash():
            logger.warning("Block #%d rejected — hash does not match payload", block.index)
            return False

        self.chain.append(block)
        logger.info("Block #%d added — hash: %s", block.index, block.hash[:16])
        return True

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def is_valid_chain(self) -> bool:
        """Return True if every block's hash and linkage are intact.

        Checks performed for each block after the genesis:
          - Stored hash matches recomputed hash (tamper detection).
          - previous_hash matches the actual previous block's hash (linkage).
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.compute_hash():
                logger.warning("Chain invalid — block #%d hash mismatch", i)
                return False

            if current.previous_hash != previous.hash:
                logger.warning("Chain invalid — block #%d linkage broken", i)
                return False

        return True
