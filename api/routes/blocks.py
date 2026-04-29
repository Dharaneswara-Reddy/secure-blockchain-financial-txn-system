"""Block endpoints — list and retrieve mined blocks."""

from flask import Blueprint, jsonify

from api.state import get_node

blocks_bp = Blueprint("blocks", __name__)


@blocks_bp.route("/blocks", methods=["GET"])
def list_blocks():
    """Return all blocks in the chain.

    Response::

        {"blocks": [...], "count": <int>}
    """
    node = get_node()
    blocks = [b.to_dict() for b in node.blockchain.chain]
    return jsonify({"blocks": blocks, "count": len(blocks)})


@blocks_bp.route("/blocks/<int:index>", methods=["GET"])
def get_block(index: int):
    """Return a single block by chain index.

    Args:
        index: Zero-based block index (0 = genesis).

    Returns:
        Block dict on success, 404 JSON on out-of-range.
    """
    node = get_node()
    if index < 0 or index >= node.blockchain.height():
        return jsonify({"error": f"Block {index} not found"}), 404
    return jsonify(node.blockchain.chain[index].to_dict())
