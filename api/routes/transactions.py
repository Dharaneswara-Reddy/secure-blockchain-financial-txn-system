"""Transaction endpoints — mempool feed and submission."""

from flask import Blueprint, jsonify, request

from api.state import get_node

transactions_bp = Blueprint("transactions", __name__)

_REQUIRED_FIELDS = {"sender", "receiver", "amount"}


@transactions_bp.route("/transactions/pending", methods=["GET"])
def get_pending():
    """Return all transactions currently in the mempool.

    Response::

        {"transactions": [...], "count": <int>}
    """
    node = get_node()
    txs = node.blockchain.mempool.get_all()
    return jsonify({"transactions": txs, "count": len(txs)})


@transactions_bp.route("/transactions/submit", methods=["POST"])
def submit_transaction():
    """Submit a new transaction to the mempool.

    Body (JSON)::

        {"sender": "0x...", "receiver": "0x...", "amount": 1.5, "fee": 0.001}

    ``fee`` is optional (defaults to 0.001).

    Returns:
        201 with ``{"tx_id": "...", "status": "pending"}`` on success.
        400 if required fields are missing.
    """
    data = request.get_json(force=True) or {}
    missing = _REQUIRED_FIELDS - data.keys()
    if missing:
        return jsonify({"error": f"Missing required fields: {sorted(missing)}"}), 400

    node = get_node()
    tx = {
        "sender": str(data["sender"]),
        "receiver": str(data["receiver"]),
        "amount": float(data["amount"]),
        "fee": float(data.get("fee", 0.001)),
    }

    try:
        tx_id = node.blockchain.mempool.add_transaction(tx)
    except OverflowError as exc:
        return jsonify({"error": str(exc)}), 503

    return jsonify({"tx_id": tx_id, "status": "pending"}), 201
