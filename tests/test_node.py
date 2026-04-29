"""Tests for chain.node — multi-node network simulation and Nakamoto sync."""

from chain.node import Node

_MINER = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"


def _node(name: str) -> Node:
    """Create a fast-mining test node (difficulty=1)."""
    return Node(node_id=name, difficulty=1)


class TestNodeInit:
    def test_starts_with_genesis(self):
        n = _node("A")
        assert n.blockchain.height() == 1

    def test_node_id_stored(self):
        n = _node("A")
        assert n.node_id == "A"

    def test_difficulty_configurable(self):
        n = Node("A", difficulty=2)
        assert n.difficulty == 2


class TestAddPeer:
    def test_peer_added(self):
        a, b = _node("A"), _node("B")
        a.add_peer(b)
        assert b in a.peers

    def test_no_self_loop(self):
        a = _node("A")
        a.add_peer(a)
        assert a not in a.peers

    def test_idempotent(self):
        a, b = _node("A"), _node("B")
        a.add_peer(b)
        a.add_peer(b)
        assert a.peers.count(b) == 1


class TestMining:
    def test_mine_creates_new_block(self):
        n = _node("A")
        n.mine_pending_transactions(_MINER)
        assert n.blockchain.height() == 2

    def test_mined_block_has_coinbase(self):
        n = _node("A")
        block = n.mine_pending_transactions(_MINER)
        assert any(tx.get("type") == "coinbase" for tx in block.transactions)

    def test_chain_valid_after_mining(self):
        n = _node("A")
        n.mine_pending_transactions(_MINER)
        assert n.blockchain.is_valid_chain()

    def test_mempool_cleared_after_mining(self):
        n = _node("A")
        n.blockchain.mempool.add_transaction({"sender": "X", "receiver": "Y", "amount": 1})
        n.mine_pending_transactions(_MINER)
        assert n.blockchain.mempool.pending_count() == 0


class TestMultiNodeBroadcast:
    def test_mined_block_propagates_to_peer(self):
        a, b = _node("A"), _node("B")
        a.add_peer(b)
        b.add_peer(a)

        a.mine_pending_transactions(_MINER)
        assert b.blockchain.height() == 2

    def test_both_chains_valid_after_broadcast(self):
        a, b = _node("A"), _node("B")
        a.add_peer(b)
        b.add_peer(a)

        a.mine_pending_transactions(_MINER)
        assert a.blockchain.is_valid_chain()
        assert b.blockchain.is_valid_chain()

    def test_three_node_propagation(self):
        a, b, c = _node("A"), _node("B"), _node("C")
        a.add_peer(b)
        b.add_peer(c)
        a.add_peer(c)

        a.mine_pending_transactions(_MINER)
        assert b.blockchain.height() == 2
        assert c.blockchain.height() == 2


class TestChainSync:
    def test_node_syncs_to_longer_chain(self):
        a, b = _node("A"), _node("B")

        # a mines 3 blocks without b knowing
        a.mine_pending_transactions(_MINER)
        a.mine_pending_transactions(_MINER)
        a.mine_pending_transactions(_MINER)

        # b has only genesis; syncing should adopt a's chain
        synced = b.sync_chain(a)
        assert synced is True
        assert b.blockchain.height() == a.blockchain.height()

    def test_sync_does_not_replace_with_shorter_chain(self):
        a, b = _node("A"), _node("B")
        a.mine_pending_transactions(_MINER)

        synced = a.sync_chain(b)  # b has only genesis — shorter
        assert synced is False
        assert a.blockchain.height() == 2

    def test_sync_rejects_invalid_chain(self):
        a, b = _node("A"), _node("B")
        a.mine_pending_transactions(_MINER)
        a.mine_pending_transactions(_MINER)

        # Corrupt b's chain and then try to get a to sync to it
        b.blockchain.chain = a.blockchain.chain[:]
        b.blockchain.chain[1].transactions.append({"tampered": True})  # break validity
        synced = a.sync_chain(b)
        assert synced is False


class TestNodeStatus:
    def test_status_has_expected_keys(self):
        n = _node("A")
        s = n.status()
        assert {"node_id", "height", "difficulty", "pending_txs", "chain_valid", "last_hash"} == set(s.keys())
