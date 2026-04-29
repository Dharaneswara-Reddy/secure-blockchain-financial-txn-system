"""
Proof-of-Work consensus mechanism.

Implements:
  - ``mine_block``       — iterates nonces until the block hash satisfies the
                           difficulty target (leading zeros).
  - ``validate_proof``   — verifies that a block's hash meets difficulty.
  - ``adjust_difficulty`` — recalculates difficulty every N blocks based on
                            actual vs. target block-production time.

Difficulty is expressed as the number of leading zero hex characters required
in a block's SHA-256 hash.  A difficulty of 3 means the hash must start with
at least "000".

Usage::

    from chain.consensus import mine_block, validate_proof, DEFAULT_DIFFICULTY

    mined = mine_block(block, difficulty=3)
    assert validate_proof(mined, difficulty=3)
"""

import time

from chain.block import Block
from wallet.config import configure_logging

logger = configure_logging(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_DIFFICULTY: int = 3
"""Starting difficulty (3 leading zero hex digits ≈ 1/4096 probability per hash)."""

DIFFICULTY_ADJUSTMENT_INTERVAL: int = 10
"""Recalculate difficulty every this many blocks."""

TARGET_BLOCK_TIME_SECONDS: float = 10.0
"""Desired average seconds between blocks."""


# ── Core functions ────────────────────────────────────────────────────────────


def mine_block(block: Block, difficulty: int = DEFAULT_DIFFICULTY) -> Block:
    """Find a nonce so that block.hash starts with *difficulty* zero hex chars.

    Mutates *block* in place (sets ``nonce`` and ``hash``) and also returns it.

    Args:
        block:      Block to mine.  Should have all fields set except nonce/hash.
        difficulty: Number of leading zero hex digits required.

    Returns:
        The same *block* object with ``nonce`` and ``hash`` updated.
    """
    prefix = "0" * difficulty
    block.nonce = 0
    block.hash = block.compute_hash()

    start = time.time()
    while not block.hash.startswith(prefix):
        block.nonce += 1
        block.hash = block.compute_hash()

    elapsed = time.time() - start
    logger.info(
        "Block #%d mined in %.3fs — nonce=%d hash=%s",
        block.index,
        elapsed,
        block.nonce,
        block.hash[:16],
    )
    return block


def validate_proof(block: Block, difficulty: int = DEFAULT_DIFFICULTY) -> bool:
    """Return True if *block* satisfies the PoW difficulty target.

    Checks both:
      - The stored hash starts with *difficulty* zeros (meets target).
      - The stored hash equals the recomputed hash (no tampering).

    Args:
        block:      Block to validate.
        difficulty: Expected leading-zero count.

    Returns:
        ``True`` if valid, ``False`` otherwise.
    """
    prefix = "0" * difficulty
    return block.hash.startswith(prefix) and block.hash == block.compute_hash()


def adjust_difficulty(chain: list[Block], current_difficulty: int) -> int:
    """Recalculate PoW difficulty based on recent block production speed.

    Called every :data:`DIFFICULTY_ADJUSTMENT_INTERVAL` blocks.  If blocks
    are produced too fast, difficulty increases by 1; too slow, decreases by 1
    (minimum 1).  Otherwise the current difficulty is returned unchanged.

    Args:
        chain:              The full chain list (``Blockchain.chain``).
        current_difficulty: Difficulty used when mining the last block.

    Returns:
        The new difficulty level (integer ≥ 1).
    """
    if len(chain) < DIFFICULTY_ADJUSTMENT_INTERVAL + 1:
        return current_difficulty

    newest = chain[-1]
    oldest = chain[-DIFFICULTY_ADJUSTMENT_INTERVAL]
    elapsed = newest.timestamp - oldest.timestamp

    expected = DIFFICULTY_ADJUSTMENT_INTERVAL * TARGET_BLOCK_TIME_SECONDS

    if elapsed <= 0 or elapsed < expected / 2:
        new_difficulty = current_difficulty + 1
        logger.info(
            "Difficulty increased %d → %d (blocks too fast: %.1fs vs %.1fs target)",
            current_difficulty,
            new_difficulty,
            elapsed,
            expected,
        )
        return new_difficulty
    elif elapsed > expected * 2:
        new_difficulty = max(1, current_difficulty - 1)
        logger.info(
            "Difficulty decreased %d → %d (blocks too slow: %.1fs vs %.1fs target)",
            current_difficulty,
            new_difficulty,
            elapsed,
            expected,
        )
        return new_difficulty

    return current_difficulty
