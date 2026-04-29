"""Tests for chain.merkle — Merkle tree root hash computation."""

from chain.merkle import build_merkle_tree, _sha256


class TestBuildMerkleTree:
    def test_empty_list_returns_hash_of_empty_string(self):
        result = build_merkle_tree([])
        assert result == _sha256("")
        assert len(result) == 64

    def test_single_transaction_returns_leaf_hash(self):
        tx = {"sender": "A", "receiver": "B", "amount": 1.0}
        result = build_merkle_tree([tx])
        assert len(result) == 64

    def test_two_transactions_deterministic(self):
        txs = [{"a": 1}, {"b": 2}]
        assert build_merkle_tree(txs) == build_merkle_tree(txs)

    def test_order_matters(self):
        tx1 = {"sender": "A", "receiver": "B", "amount": 1.0}
        tx2 = {"sender": "B", "receiver": "C", "amount": 2.0}
        assert build_merkle_tree([tx1, tx2]) != build_merkle_tree([tx2, tx1])

    def test_odd_number_of_transactions(self):
        txs = [{"id": i} for i in range(3)]
        result = build_merkle_tree(txs)
        assert len(result) == 64

    def test_even_number_of_transactions(self):
        txs = [{"id": i} for i in range(4)]
        result = build_merkle_tree(txs)
        assert len(result) == 64

    def test_large_set(self):
        txs = [{"id": i, "amount": float(i)} for i in range(100)]
        result = build_merkle_tree(txs)
        assert len(result) == 64

    def test_different_transactions_different_root(self):
        txs_a = [{"sender": "A", "receiver": "B", "amount": 1.0}]
        txs_b = [{"sender": "A", "receiver": "B", "amount": 2.0}]
        assert build_merkle_tree(txs_a) != build_merkle_tree(txs_b)

    def test_adding_transaction_changes_root(self):
        txs = [{"id": 1}]
        root1 = build_merkle_tree(txs)
        txs.append({"id": 2})
        root2 = build_merkle_tree(txs)
        assert root1 != root2
