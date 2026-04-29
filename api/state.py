"""
Global in-memory node singleton for the Flask API.

The Node (and its embedded Blockchain + Mempool) persists for the lifetime
of the Flask process.  Call ``reset_node()`` in tests to get a clean slate.
"""

from chain.node import Node

_node: Node | None = None
_DEFAULT_DIFFICULTY = 3


def get_node() -> Node:
    """Return the global Node, creating it lazily on first call."""
    global _node
    if _node is None:
        _node = Node("api-node", difficulty=_DEFAULT_DIFFICULTY)
    return _node


def reset_node() -> None:
    """Destroy the current node (used in tests to start fresh)."""
    global _node
    _node = None
