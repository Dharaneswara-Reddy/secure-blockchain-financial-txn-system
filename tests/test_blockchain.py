"""Tests for chain.blockchain — chain creation, block addition, and validation."""

from chain.block import Block, GENESIS_PREV_HASH
from chain.blockchain import Blockchain


class TestGenesisBlock:
    def test_chain_starts_with_one_block(self):
        bc = Blockchain()
        assert bc.height() == 1

    def test_genesis_has_index_zero(self):
        bc = Blockchain()
        assert bc.chain[0].index == 0

    def test_genesis_prev_hash_is_zeros(self):
        bc = Blockchain()
        assert bc.chain[0].previous_hash == GENESIS_PREV_HASH

    def test_genesis_hash_is_valid(self):
        bc = Blockchain()
        genesis = bc.chain[0]
        assert genesis.hash == genesis.compute_hash()

    def test_genesis_has_no_transactions(self):
        bc = Blockchain()
        assert bc.chain[0].transactions == []

    def test_deterministic_genesis_with_fixed_timestamp(self):
        bc1 = Blockchain(genesis_timestamp=0.0)
        bc2 = Blockchain(genesis_timestamp=0.0)
        assert bc1.chain[0].hash == bc2.chain[0].hash


class TestAddBlock:
    def _make_block(self, bc: Blockchain, index: int = 1) -> Block:
        last = bc.last_block()
        b = Block(index=index, transactions=[], previous_hash=last.hash, timestamp=float(index))
        return b

    def test_valid_block_accepted(self):
        bc = Blockchain()
        b = self._make_block(bc)
        assert bc.add_block(b) is True
        assert bc.height() == 2

    def test_wrong_previous_hash_rejected(self):
        bc = Blockchain()
        b = Block(index=1, transactions=[], previous_hash="wrong" * 12, timestamp=1.0)
        assert bc.add_block(b) is False
        assert bc.height() == 1

    def test_tampered_hash_rejected(self):
        bc = Blockchain()
        b = self._make_block(bc)
        b.hash = "tampered" * 8  # manually corrupt
        assert bc.add_block(b) is False

    def test_chain_grows_correctly(self):
        bc = Blockchain()
        for i in range(1, 6):
            b = Block(index=i, transactions=[], previous_hash=bc.last_block().hash, timestamp=float(i))
            assert bc.add_block(b) is True
        assert bc.height() == 6


class TestChainValidation:
    def test_fresh_chain_is_valid(self):
        bc = Blockchain()
        assert bc.is_valid_chain() is True

    def test_multi_block_chain_is_valid(self):
        bc = Blockchain()
        for i in range(1, 4):
            b = Block(index=i, transactions=[], previous_hash=bc.last_block().hash, timestamp=float(i))
            bc.add_block(b)
        assert bc.is_valid_chain() is True

    def test_tampered_data_invalidates_chain(self):
        bc = Blockchain()
        b = Block(index=1, transactions=[], previous_hash=bc.last_block().hash, timestamp=1.0)
        bc.add_block(b)
        # Tamper without recomputing hash
        bc.chain[1].transactions.append({"tampered": True})
        assert bc.is_valid_chain() is False

    def test_broken_linkage_invalidates_chain(self):
        bc = Blockchain()
        b = Block(index=1, transactions=[], previous_hash=bc.last_block().hash, timestamp=1.0)
        bc.add_block(b)
        bc.chain[1].previous_hash = "broken" * 10
        assert bc.is_valid_chain() is False


class TestHelpers:
    def test_total_transactions_counts_all(self):
        bc = Blockchain()
        txs = [{"sender": "A", "receiver": "B", "amount": 1.0}]
        b = Block(index=1, transactions=txs, previous_hash=bc.last_block().hash, timestamp=1.0)
        bc.add_block(b)
        assert bc.total_transactions() == 1

    def test_last_block_returns_most_recent(self):
        bc = Blockchain()
        b = Block(index=1, transactions=[], previous_hash=bc.last_block().hash, timestamp=1.0)
        bc.add_block(b)
        assert bc.last_block() is b
