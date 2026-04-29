"""Tests for chain.mempool — transaction pool operations."""

import pytest
from chain.mempool import Mempool


_TX = {"sender": "0xAlice", "receiver": "0xBob", "amount": 1.5, "fee": 0.001}


class TestAddTransaction:
    def test_returns_string_id(self):
        pool = Mempool()
        tx_id = pool.add_transaction(_TX)
        assert isinstance(tx_id, str)
        assert len(tx_id) > 0

    def test_unique_ids(self):
        pool = Mempool()
        ids = {pool.add_transaction(_TX) for _ in range(10)}
        assert len(ids) == 10

    def test_entry_has_id_and_timestamp(self):
        pool = Mempool()
        tx_id = pool.add_transaction(_TX)
        entry = pool.get_all()[0]
        assert entry["id"] == tx_id
        assert "submitted_at" in entry

    def test_original_fields_preserved(self):
        pool = Mempool()
        pool.add_transaction(_TX)
        entry = pool.get_all()[0]
        assert entry["sender"] == _TX["sender"]
        assert entry["amount"] == _TX["amount"]

    def test_overflow_raises(self):
        pool = Mempool(max_size=2)
        pool.add_transaction(_TX)
        pool.add_transaction(_TX)
        with pytest.raises(OverflowError):
            pool.add_transaction(_TX)


class TestSelectTransactions:
    def test_returns_fifo_order(self):
        pool = Mempool()
        id1 = pool.add_transaction({"sender": "A", "receiver": "B", "amount": 1})
        id2 = pool.add_transaction({"sender": "C", "receiver": "D", "amount": 2})
        selected = pool.select_transactions(max_count=2)
        assert selected[0]["id"] == id1
        assert selected[1]["id"] == id2

    def test_respects_max_count(self):
        pool = Mempool()
        for _ in range(20):
            pool.add_transaction(_TX)
        assert len(pool.select_transactions(max_count=5)) == 5

    def test_non_destructive(self):
        pool = Mempool()
        pool.add_transaction(_TX)
        pool.select_transactions()
        assert pool.pending_count() == 1


class TestRemoveTransactions:
    def test_removes_by_id(self):
        pool = Mempool()
        tx_id = pool.add_transaction(_TX)
        pool.remove_transactions([tx_id])
        assert pool.pending_count() == 0

    def test_unknown_id_ignored(self):
        pool = Mempool()
        pool.add_transaction(_TX)
        pool.remove_transactions(["nonexistent-id"])
        assert pool.pending_count() == 1

    def test_returns_count_removed(self):
        pool = Mempool()
        id1 = pool.add_transaction(_TX)
        id2 = pool.add_transaction(_TX)
        removed = pool.remove_transactions([id1, id2])
        assert removed == 2


class TestPendingCount:
    def test_zero_initially(self):
        assert Mempool().pending_count() == 0

    def test_increases_on_add(self):
        pool = Mempool()
        pool.add_transaction(_TX)
        assert pool.pending_count() == 1

    def test_len_equals_pending_count(self):
        pool = Mempool()
        pool.add_transaction(_TX)
        assert len(pool) == pool.pending_count()


class TestClear:
    def test_empties_pool(self):
        pool = Mempool()
        pool.add_transaction(_TX)
        pool.clear()
        assert pool.pending_count() == 0
