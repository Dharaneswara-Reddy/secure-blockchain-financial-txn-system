"""
Demo script — Shows transactions on Ethereum (Ganache) via the smart contract.

Prerequisites:
  1. Ganache GUI running on http://127.0.0.1:7545
  2. Contract deployed: npx hardhat run scripts/deploy.js --network ganache
  3. Run this: python demo_ethereum.py

This script will:
  - Connect to Ganache
  - Fund two wallets on-chain
  - Submit a transaction (sender → receiver)
  - Approve the transaction
  - Show all balances and events on Ethereum
"""

from web3 import Web3
from blockchain.contract import ContractInterface

# ── Connect to Ganache / Hardhat ─────────────────────────────
w3 = None
for port in [7545, 8545]:
    try:
        temp_w3 = Web3(Web3.HTTPProvider(f"http://127.0.0.1:{port}"))
        if temp_w3.is_connected():
            w3 = temp_w3
            break
    except Exception:
        continue

if not w3:
    print("❌ Cannot connect to Ganache (port 7545) or Hardhat localhost (port 8545).")
    print("   Please make sure Ganache GUI is running or run: npx hardhat node")
    exit(1)

print(f"✅ Connected to local network on port {w3.provider.endpoint_uri.split(':')[-1]}")
print(f"   Chain ID : {w3.eth.chain_id}")
print(f"   Block    : {w3.eth.block_number}")
print()

# ── Load deployed contract ──────────────────────────────────
ci = ContractInterface.from_deployment_file(w3)
print(f"✅ Contract loaded at: {ci.contract.address}")
print()

# ── Get Ganache accounts ────────────────────────────────────
accounts = w3.eth.accounts
owner    = accounts[0]   # contract deployer / owner
sender   = accounts[1]   # Alice
receiver = accounts[2]   # Bob

print("=" * 60)
print("  ACCOUNTS")
print("=" * 60)
print(f"  Owner    : {owner}")
print(f"  Sender   : {sender}  (Alice)")
print(f"  Receiver : {receiver}  (Bob)")
print()

# ── Step 1: Fund wallets ────────────────────────────────────
print("=" * 60)
print("  STEP 1: Fund Wallets (deposit ETH into contract)")
print("=" * 60)

fund_amount = 10.0  # 10 ETH

receipt1 = ci.fund_wallet(sender, fund_amount, owner)
print(f"  ✅ Funded Alice with 10 ETH — tx: {receipt1.transactionHash.hex()[:20]}...")

receipt2 = ci.fund_wallet(receiver, 5.0, owner)
print(f"  ✅ Funded Bob with 5 ETH   — tx: {receipt2.transactionHash.hex()[:20]}...")
print()

# Show balances
alice_bal = ci.get_balance(sender)
bob_bal   = ci.get_balance(receiver)
print(f"  Alice balance: {alice_bal} ETH")
print(f"  Bob balance:   {bob_bal} ETH")
print()

# ── Step 2: Submit a transaction ────────────────────────────
print("=" * 60)
print("  STEP 2: Alice sends 2 ETH to Bob (fee: 0.1 ETH)")
print("=" * 60)

value = 2.0
fee   = 0.1

tx_hash = ci.submit_transaction(sender, receiver, value, fee)
print(f"  ✅ Transaction submitted!")
print(f"     On-chain TX hash: {tx_hash.hex()[:20]}...")
print()

# Show the pending transaction
tx_record = ci.get_transaction(tx_hash)
print(f"  Transaction record on Ethereum:")
print(f"     Sender:   {tx_record['sender']}")
print(f"     Receiver: {tx_record['receiver']}")
print(f"     Value:    {tx_record['value_ether']} ETH")
print(f"     Fee:      {tx_record['fee_ether']} ETH")
print(f"     Status:   {tx_record['status']}")
print()

# Show updated balances (Alice is debited immediately due to CEI)
alice_bal = ci.get_balance(sender)
bob_bal   = ci.get_balance(receiver)
print(f"  After submit (CEI — deducted immediately):")
print(f"     Alice balance: {alice_bal} ETH  (was 10, now 10 - 2 - 0.1 = 7.9)")
print(f"     Bob balance:   {bob_bal} ETH  (unchanged, still pending)")
print()

# ── Step 3: Approve the transaction ─────────────────────────
print("=" * 60)
print("  STEP 3: Owner approves the transaction")
print("=" * 60)

receipt4 = ci.approve_transaction(tx_hash, owner)
print(f"  ✅ Transaction APPROVED!")
print(f"     Ethereum TX hash: {receipt4.transactionHash.hex()[:20]}...")
print()

# Final balances
alice_bal = ci.get_balance(sender)
bob_bal   = ci.get_balance(receiver)
print(f"  Final balances:")
print(f"     Alice: {alice_bal} ETH")
print(f"     Bob:   {bob_bal} ETH  (was 5, now 5 + 2 = 7)")
print()

# Final transaction status
tx_record = ci.get_transaction(tx_hash)
print(f"  Final TX status: {tx_record['status']}")
print()

# ── Step 4: Show all events on Ethereum ─────────────────────
print("=" * 60)
print("  ALL EVENTS ON ETHEREUM (visible on Ganache)")
print("=" * 60)

submitted = ci.get_submitted_events()
approved  = ci.get_approved_events()
print(f"  Submitted events: {len(submitted)}")
for e in submitted:
    print(f"     → sender={e.get('sender','?')}, receiver={e.get('receiver','?')}")

print(f"  Approved events:  {len(approved)}")
for e in approved:
    print(f"     → txHash={e.get('txHash', b'?').hex()[:20]}...")

print()
print(f"  Total transactions on contract: {ci.get_tx_count()}")
print()
print("=" * 60)
print("  ✅ DEMO COMPLETE — All transactions are on Ethereum!")
print("  Open Ganache GUI → Transactions tab to see them")
print("=" * 60)
