"""
Node — simulates a participant in a blockchain peer-to-peer network.

Each Node wraps a Blockchain and handles:
  - Mining pending transactions into new blocks.
  - Broadcasting newly mined blocks to peer nodes.
  - Receiving blocks from peers and validating them.
  - Syncing to the longest valid chain (Nakamoto consensus).

Usage::

    node_a = Node("A", difficulty=1)
    node_b = Node("B", difficulty=1)
    node_a.add_peer(node_b)
    node_b.add_peer(node_a)

    node_a.blockchain.mempool.add_transaction({"sender": "X", "receiver": "Y", "amount": 5})
    block = node_a.mine_pending_transactions(miner_address="0xMINER")
    # node_b automatically receives the block via broadcast
    assert node_b.blockchain.height() == node_a.blockchain.height()
"""

import time
from typing import TYPE_CHECKING

from chain.block import Block
from chain.blockchain import Blockchain
from chain.consensus import DEFAULT_DIFFICULTY, adjust_difficulty, mine_block, validate_proof
from wallet.config import configure_logging

if TYPE_CHECKING:
    pass  # avoid circular imports

logger = configure_logging(__name__)

_COINBASE_REWARD: float = 50.0
"""Block reward credited to the miner in each mined block."""


class Node:
    """Simulates a single blockchain network participant.

    Args:
        node_id:    Human-readable identifier for this node.
        difficulty: Initial PoW difficulty.  Use 1 in tests for speed.
    """

    def __init__(self, node_id: str, difficulty: int = DEFAULT_DIFFICULTY) -> None:
        self.node_id = node_id
        self.blockchain = Blockchain()
        self.difficulty = difficulty
        self.peers: list["Node"] = []

    # ------------------------------------------------------------------
    # Peer management
    # ------------------------------------------------------------------

    def add_peer(self, peer: "Node") -> None:
        """Register *peer* as a network neighbour (idempotent, no self-loops)."""
        if peer is not self and peer not in self.peers:
            self.peers.append(peer)
            logger.debug("Node %s connected to peer %s", self.node_id, peer.node_id)

    # ------------------------------------------------------------------
    # Mining
    # ------------------------------------------------------------------

    def mine_pending_transactions(self, miner_address: str) -> Block | None:
        """Pull transactions from the mempool, mine a block, and broadcast.

        A coinbase (reward) transaction is prepended to every block so the
        miner always gets paid even if the mempool is empty.

        Args:
            miner_address: Ethereum-style address that receives the coinbase.

        Returns:
            The newly mined Block on success, or ``None`` if ``add_block`` fails.
        """
        pending = self.blockchain.mempool.select_transactions()
        coinbase = {
            "sender": "NETWORK",
            "receiver": miner_address,
            "amount": _COINBASE_REWARD,
            "fee": 0.0,
            "type": "coinbase",
        }
        transactions = [coinbase, *pending]

        new_block = Block(
            index=self.blockchain.height(),
            transactions=transactions,
            previous_hash=self.blockchain.last_block().hash,
            timestamp=time.time(),
        )

        mined = mine_block(new_block, self.difficulty)

        if not self.blockchain.add_block(mined):
            return None

        # Remove mined transactions from mempool
        mined_ids = [tx["id"] for tx in pending if "id" in tx]
        self.blockchain.mempool.remove_transactions(mined_ids)

        # Adjust difficulty for next block
        self.difficulty = adjust_difficulty(self.blockchain.chain, self.difficulty)

        # Broadcast to peers
        self._broadcast(mined)
        return mined

    # ------------------------------------------------------------------
    # P2P message handlers
    # ------------------------------------------------------------------

    def _broadcast(self, block: Block) -> None:
        """Send *block* to every peer node."""
        for peer in self.peers:
            peer.receive_block(block, sender=self)

    def receive_block(self, block: Block, sender: "Node") -> bool:
        """Accept a block received from a peer.

        If the block extends our chain and passes PoW validation it is added.
        If the sender has a longer valid chain we sync to it instead.

        Args:
            block:  Block propagated by *sender*.
            sender: The Node that sent the block.

        Returns:
            ``True`` if the block was added to our chain.
        """
        if block.previous_hash == self.blockchain.last_block().hash:
            if validate_proof(block, self.difficulty):
                added = self.blockchain.add_block(block)
                if added:
                    logger.info("Node %s accepted block #%d from %s", self.node_id, block.index, sender.node_id)
                return added

        # Our chains diverged — sync if the sender has a longer valid chain
        if len(sender.blockchain.chain) > self.blockchain.height():
            return self.sync_chain(sender)

        return False

    def sync_chain(self, peer: "Node") -> bool:
        """Replace our chain with *peer*'s if it is longer and valid.

        Implements the Nakamoto "longest valid chain" rule.

        Args:
            peer: The Node whose chain we evaluate.

        Returns:
            ``True`` if we replaced our chain.
        """
        peer_chain = peer.blockchain.chain
        if len(peer_chain) > self.blockchain.height() and peer.blockchain.is_valid_chain():
            self.blockchain.chain = list(peer_chain)
            logger.info(
                "Node %s synced chain from %s — new height: %d",
                self.node_id,
                peer.node_id,
                len(peer_chain),
            )
            return True
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Return a summary dict for logging or API responses."""
        return {
            "node_id": self.node_id,
            "height": self.blockchain.height(),
            "difficulty": self.difficulty,
            "pending_txs": self.blockchain.mempool.pending_count(),
            "chain_valid": self.blockchain.is_valid_chain(),
            "last_hash": self.blockchain.last_block().hash[:16],
        }
