"""Tests for the Flask REST API — all endpoints via test_client (no live server)."""

import json
import pytest

from api.app import create_app
from api.state import reset_node


@pytest.fixture(autouse=True)
def fresh_node():
    """Reset in-memory node before every test."""
    reset_node()
    yield
    reset_node()


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _mine(client, miner: str = "0xMINER") -> dict:
    resp = client.post("/api/mine", json={"miner_address": miner})
    return resp


# ── /api/blocks ──────────────────────────────────────────────────────────────


class TestListBlocks:
    def test_returns_200(self, client):
        resp = client.get("/api/blocks")
        assert resp.status_code == 200

    def test_includes_genesis(self, client):
        data = resp_json(client.get("/api/blocks"))
        assert data["count"] == 1
        assert data["blocks"][0]["index"] == 0

    def test_count_grows_after_mining(self, client):
        _mine(client)
        data = resp_json(client.get("/api/blocks"))
        assert data["count"] == 2


class TestGetBlock:
    def test_genesis_returned(self, client):
        data = resp_json(client.get("/api/blocks/0"))
        assert data["index"] == 0

    def test_404_for_missing_block(self, client):
        resp = client.get("/api/blocks/999")
        assert resp.status_code == 404

    def test_returns_mined_block(self, client):
        _mine(client)
        data = resp_json(client.get("/api/blocks/1"))
        assert data["index"] == 1


# ── /api/transactions ─────────────────────────────────────────────────────────


class TestPendingTransactions:
    def test_empty_on_start(self, client):
        data = resp_json(client.get("/api/transactions/pending"))
        assert data["count"] == 0

    def test_count_after_submit(self, client):
        client.post("/api/transactions/submit", json={"sender": "A", "receiver": "B", "amount": 1})
        data = resp_json(client.get("/api/transactions/pending"))
        assert data["count"] == 1


class TestSubmitTransaction:
    def test_201_on_valid(self, client):
        resp = client.post("/api/transactions/submit", json={"sender": "A", "receiver": "B", "amount": 5})
        assert resp.status_code == 201

    def test_returns_tx_id(self, client):
        data = resp_json(client.post("/api/transactions/submit", json={"sender": "A", "receiver": "B", "amount": 1}))
        assert "tx_id" in data
        assert data["status"] == "pending"

    def test_400_missing_fields(self, client):
        resp = client.post("/api/transactions/submit", json={"sender": "A"})
        assert resp.status_code == 400

    def test_400_empty_body(self, client):
        resp = client.post("/api/transactions/submit", json={})
        assert resp.status_code == 400


# ── /api/chain ───────────────────────────────────────────────────────────────


class TestChainStats:
    def test_200_and_required_keys(self, client):
        data = resp_json(client.get("/api/chain/stats"))
        expected = {"height", "total_transactions", "difficulty", "pending_transactions", "last_hash", "last_block_index", "is_valid"}
        assert expected.issubset(data.keys())

    def test_height_is_one_initially(self, client):
        data = resp_json(client.get("/api/chain/stats"))
        assert data["height"] == 1


class TestValidateChain:
    def test_valid_on_fresh_chain(self, client):
        data = resp_json(client.get("/api/chain/validate"))
        assert data["valid"] is True

    def test_invalid_after_tamper(self, client):
        _mine(client)
        client.post("/api/tamper/1")
        data = resp_json(client.get("/api/chain/validate"))
        assert data["valid"] is False


class TestMine:
    def test_201_on_success(self, client):
        resp = _mine(client)
        assert resp.status_code == 201

    def test_returns_block(self, client):
        data = resp_json(_mine(client))
        assert "block" in data
        assert data["block"]["index"] == 1

    def test_height_increases(self, client):
        _mine(client)
        data = resp_json(client.get("/api/chain/stats"))
        assert data["height"] == 2


# ── /api/tamper ───────────────────────────────────────────────────────────────


class TestTamper:
    def test_400_on_genesis(self, client):
        resp = client.post("/api/tamper/0")
        assert resp.status_code == 400

    def test_400_out_of_range(self, client):
        resp = client.post("/api/tamper/99")
        assert resp.status_code == 400

    def test_tamper_breaks_validity(self, client):
        _mine(client)
        data = resp_json(client.post("/api/tamper/1"))
        assert data["chain_valid"] is False
        assert data["hash_mismatch"] is True

    def test_restore_resets_chain(self, client):
        _mine(client)
        client.post("/api/tamper/1")
        data = resp_json(client.post("/api/chain/restore"))
        assert data["chain_valid"] is True
        assert data["height"] == 1


# ── helpers ───────────────────────────────────────────────────────────────────


def resp_json(response) -> dict:
    return json.loads(response.data)
