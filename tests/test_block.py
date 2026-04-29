"""Tests for chain.block — Block dataclass and SHA-256 hashing."""

import time
from chain.block import Block, GENESIS_PREV_HASH, _sha256


class TestSha256Helper:
    def test_returns_64_hex_chars(self):
        result = _sha256("hello")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        assert _sha256("blockchain") == _sha256("blockchain")

    def test_different_inputs_differ(self):
        assert _sha256("abc") != _sha256("def")


class TestBlockCreation:
    def test_hash_set_on_init(self):
        b = Block(index=0, transactions=[], previous_hash=GENESIS_PREV_HASH, timestamp=0.0)
        assert b.hash != ""
        assert len(b.hash) == 64

    def test_hash_equals_compute_hash(self):
        b = Block(index=1, transactions=[], previous_hash="a" * 64, timestamp=1.0)
        assert b.hash == b.compute_hash()

    def test_provided_hash_not_overwritten(self):
        b = Block(index=0, transactions=[], previous_hash=GENESIS_PREV_HASH, timestamp=0.0, hash="preset")
        assert b.hash == "preset"

    def test_default_nonce_is_zero(self):
        b = Block(index=0, transactions=[], previous_hash=GENESIS_PREV_HASH, timestamp=0.0)
        assert b.nonce == 0

    def test_timestamp_defaults_to_current_time(self):
        before = time.time()
        b = Block(index=0, transactions=[], previous_hash=GENESIS_PREV_HASH)
        after = time.time()
        assert before <= b.timestamp <= after


class TestBlockHashing:
    def test_hash_is_deterministic(self):
        b1 = Block(index=1, transactions=[], previous_hash="0" * 64, timestamp=100.0, nonce=0)
        b2 = Block(index=1, transactions=[], previous_hash="0" * 64, timestamp=100.0, nonce=0)
        assert b1.compute_hash() == b2.compute_hash()

    def test_changing_index_changes_hash(self):
        b = Block(index=1, transactions=[], previous_hash="0" * 64, timestamp=100.0, nonce=0)
        h1 = b.compute_hash()
        b.index = 2
        assert b.compute_hash() != h1

    def test_changing_nonce_changes_hash(self):
        b = Block(index=1, transactions=[], previous_hash="0" * 64, timestamp=100.0, nonce=0)
        h1 = b.compute_hash()
        b.nonce = 1
        assert b.compute_hash() != h1

    def test_changing_transactions_changes_hash(self):
        b = Block(index=1, transactions=[], previous_hash="0" * 64, timestamp=100.0, nonce=0)
        h1 = b.compute_hash()
        b.transactions.append({"sender": "A", "receiver": "B", "amount": 1})
        assert b.compute_hash() != h1

    def test_changing_prev_hash_changes_hash(self):
        b = Block(index=1, transactions=[], previous_hash="0" * 64, timestamp=100.0, nonce=0)
        h1 = b.compute_hash()
        b.previous_hash = "f" * 64
        assert b.compute_hash() != h1

    def test_genesis_prev_hash_is_64_zeros(self):
        assert GENESIS_PREV_HASH == "0" * 64


class TestBlockToDict:
    def test_to_dict_has_all_keys(self):
        b = Block(index=0, transactions=[], previous_hash=GENESIS_PREV_HASH, timestamp=0.0)
        d = b.to_dict()
        assert {"index", "timestamp", "transactions", "previous_hash", "nonce", "hash", "tx_count"} == set(d.keys())

    def test_tx_count_matches_transactions(self):
        txs = [{"a": 1}, {"b": 2}]
        b = Block(index=1, transactions=txs, previous_hash="0" * 64, timestamp=0.0)
        assert b.to_dict()["tx_count"] == 2
