"""
Merkle tree implementation for transaction integrity.

A Merkle tree is a binary hash tree where:
  - Leaf nodes are SHA-256 hashes of individual transactions.
  - Internal nodes are SHA-256 hashes of their two children concatenated.
  - If the number of leaves at any level is odd, the last node is duplicated.
  - The root hash commits to the complete set of transactions.

Usage::

    from chain.merkle import build_merkle_tree

    root = build_merkle_tree(transactions)
"""

import hashlib
import json
from typing import Any


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _leaf_hash(tx: dict[str, Any]) -> str:
    """Deterministic hash of a single transaction dict."""
    return _sha256(json.dumps(tx, sort_keys=True, separators=(",", ":")))


def build_merkle_tree(transactions: list[dict[str, Any]]) -> str:
    """Build a Merkle tree and return the root hash.

    Args:
        transactions: Ordered list of transaction dicts.

    Returns:
        Hex-encoded SHA-256 Merkle root.  Returns the hash of an empty
        string when *transactions* is empty.
    """
    if not transactions:
        return _sha256("")

    level: list[str] = [_leaf_hash(tx) for tx in transactions]

    if len(level) == 1:
        return level[0]

    while len(level) > 1:
        # Duplicate last node if level has odd length
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [_sha256(level[i] + level[i + 1]) for i in range(0, len(level), 2)]

    return level[0]
