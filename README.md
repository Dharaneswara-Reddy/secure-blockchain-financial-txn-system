# 🔗 Secure Blockchain Financial Transaction System

> **A production-grade, end-to-end blockchain implementation** — from raw cryptographic primitives to a Solidity smart contract, a live REST API, and a browser-based Block Explorer. Built entirely from scratch in Python 3.13 + Solidity 0.8.20, demonstrating every layer of blockchain technology.

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [Architecture at a Glance](#-architecture-at-a-glance)
3. [Technology Stack](#-technology-stack)
4. [Project Phases](#-project-phases)
5. [Key Features & Technical Highlights](#-key-features--technical-highlights)
6. [Security Design](#-security-design)
7. [Getting Started](#-getting-started)
8. [Environment Variables](#-environment-variables)
9. [API Reference](#-api-reference)
10. [Smart Contract](#-smart-contract)
11. [Testing & CI/CD](#-testing--cicd)
12. [Project Structure](#-project-structure)
13. [Interview Q&A: Concepts Demonstrated](#-interview-qa-concepts-demonstrated)

---

## 🎯 Project Overview

This project implements a **secure, multi-layer blockchain financial transaction system** that mirrors the architecture used by real-world networks like Ethereum. It is built across six progressive phases:

| Layer | What was built |
|---|---|
| **Wallet Identity** | ECDSA secp256k1 key pairs, AES-256-CBC encrypted keystores, Ethereum address validation |
| **Chain Core** | Block structure, Merkle tree, Mempool, Proof-of-Work, Difficulty Adjustment |
| **P2P Network** | Multi-Node peer broadcasting, Nakamoto longest-chain consensus |
| **Smart Contract** | Solidity `TransactionContract` — fund, submit, approve, reject, on-chain events |
| **REST API** | Flask Blueprint API — mine, submit transactions, validate chain, tamper detection |
| **Block Explorer** | Browser SPA dashboard — live chain stats, block list, tamper demo |

The entire system is covered by **13 pytest test modules** with **≥80% code coverage**, enforced via a 5-stage GitHub Actions CI pipeline.

---

## 🏗 Architecture at a Glance

```
┌───────────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser / curl)                        │
└──────────────────────────────┬────────────────────────────────────────┘
                               │  HTTP
┌──────────────────────────────▼────────────────────────────────────────┐
│                     Flask REST API  (api/)                             │
│  /api/blocks  /api/transactions  /api/chain  /api/mine  /api/tamper   │
│                       api/static/index.html  (Block Explorer SPA)     │
└──────┬──────────────────────────────────────────┬──────────────────────┘
       │  uses                                    │  uses
┌──────▼──────────┐                  ┌────────────▼────────────────────┐
│   chain/ Node   │                  │   blockchain/ ContractInterface  │
│  Blockchain     │                  │   (web3.py)                      │
│  Mempool        │                  └────────────┬────────────────────┘
│  Block          │                               │  JSON-RPC
│  Merkle         │                  ┌────────────▼────────────────────┐
│  Consensus(PoW) │                  │   Ganache / Hardhat Node        │
│  Node (P2P)     │                  │   TransactionContract.sol       │
└──────┬──────────┘                  └─────────────────────────────────┘
       │  uses
┌──────▼────────────────────┐
│   wallet/                  │
│   KeyManager (ECDSA)       │
│   Signer (ECDSA-SHA256)    │
│   AddressLoader (CSV)      │
│   Config (.env)            │
│   Exceptions               │
└────────────────────────────┘
```

---

## 💻 Technology Stack

### Backend / Core
| Tool | Version | Purpose |
|---|---|---|
| **Python** | 3.13 | Core language |
| **Flask** | ≥3.1.0 | REST API framework |
| **cryptography** | ≥44.0.2 | ECDSA key management (secp256k1), AES-256-CBC |
| **web3.py** | ≥7.14.1 | Ethereum smart contract interaction |
| **pandas** | ≥2.3.3 | Ethereum CSV dataset loading & parsing |

### Smart Contract
| Tool | Version | Purpose |
|---|---|---|
| **Solidity** | 0.8.20 | Smart contract language |
| **Hardhat** | Latest | Compile, deploy, test contracts |
| **Ganache** | — | Local Ethereum test network |
| **Node.js** | 22 | Hardhat runtime |

### Testing & Quality
| Tool | Purpose |
|---|---|
| **pytest** | Unit & integration testing |
| **pytest-cov** | Code coverage (≥80% enforced) |
| **Ruff** | Linting + auto-formatting |
| **Bandit** | Static security analysis |
| **pip-audit** | Dependency CVE scanning |
| **GitHub Actions** | 5-stage CI pipeline |

---

## 📚 Project Phases

### Phase 1 — Wallet Identity Module (`wallet/`)
The foundation of the system. Every blockchain participant needs a cryptographic identity.

- Generates **ECDSA key pairs** on the **secp256k1** curve (same curve as Bitcoin and Ethereum)
- Serialises private keys as **PEM with AES-256-CBC encryption** using a passphrase-derived key (PBKDF2-HMAC via `BestAvailableEncryption`)
- Saves private key files with **POSIX `0o600` permissions** (owner-read-only)
- Loads and **validates Ethereum addresses** from real-world CSV transaction datasets using a compiled regex (`0x` + 40 hex chars)
- Provides **batch key generation** — generates and persists key pairs for every unique address found in the dataset, skipping already-generated keys (idempotent)

### Phase 2 — Transaction Signing & Verification (`wallet/signer.py`)
Ensures transactions cannot be forged or replayed.

- Signs transaction data with **ECDSA-SHA256**
- Implements **replay attack protection** — each signature embeds a UUID4 nonce; reusing the same signature on a different nonce fails verification
- Implements **signature malleability protection** following **Bitcoin BIP-62** — low-S normalisation ensures `s ≤ N/2` for every signature; high-S signatures are rejected during verification
- Uses **canonical JSON serialisation** (sorted keys, no extra whitespace) to guarantee byte-identical message encoding regardless of dict insertion order
- Signature format: **raw 64 bytes (r‖s, big-endian, 32 bytes each)** — simpler than DER and immune to DER encoding ambiguity

### Phase 3 — Smart Contract (`contracts/`, `blockchain/`)
Brings on-chain immutability and consensus to financial transactions.

- Solidity `TransactionContract` manages a complete transaction lifecycle:
  - **Fund wallets** — deposit ETH to an internal ledger (`fundWallet`)
  - **Submit** — reserves funds atomically, emits `TransactionSubmitted` event
  - **Approve** — owner credits receiver, fee stays in contract as miner reward
  - **Reject** — full refund (value + fee) to sender, rejection reason stored on-chain
- Python `ContractInterface` wraps all web3.py calls behind a clean Pythonic API
- Contract reads ABI from **Hardhat's compiled artifact** (never hardcoded)
- Deployed via `scripts/deploy.js`; address auto-saved to `deployment.json` for Python to discover

### Phase 4 — Chain Architecture (`chain/`)
The raw blockchain mechanics — the heart of the system.

- **`Block`** — SHA-256 hashed dataclass (index, timestamp, transactions, previous_hash, nonce)
- **`Merkle`** — Binary hash tree that commits to all transactions in a block; odd-length levels are padded by duplicating the last node
- **`Mempool`** — Thread-safe FIFO queue (Python `deque`) for unconfirmed transactions; UUID-tagged, overflow-protected
- **`Blockchain`** — Links blocks with previous_hash pointers; validates hash integrity and chain linkage on every `add_block`
- **`Consensus (PoW)`** — SHA-256 proof-of-work: increments nonce until hash starts with `difficulty` leading zeros; `adjust_difficulty` recalculates every 10 blocks targeting 10-second block times

### Phase 5 — P2P Network (`chain/node.py`)
Simulates a real distributed blockchain network.

- Each **`Node`** wraps a `Blockchain` and maintains a peer list
- `mine_pending_transactions` pulls from mempool, prepends a **coinbase (50 ETH reward)** transaction, mines via PoW, broadcasts to all peers
- `receive_block` validates PoW before accepting; falls back to `sync_chain` on divergence
- `sync_chain` implements **Nakamoto longest-valid-chain rule** — replaces local chain only if peer chain is longer AND passes full `is_valid_chain()` validation

### Phase 6 — REST API & Block Explorer (`api/`, `api/static/`)
The user-facing interface to the blockchain.

- **Flask application factory** (`create_app`) — registers 4 blueprints under `/api`
- **Global Node singleton** (`api/state.py`) — one `Node` instance per Flask process, reset-able for tests
- **Block Explorer SPA** served from `api/static/index.html` — live-updating dashboard

---

## 🔑 Key Features & Technical Highlights

### 1. End-to-End Cryptographic Security
- **secp256k1 ECDSA** — same curve as Bitcoin/Ethereum, enabling direct key compatibility
- **AES-256-CBC** encrypted keystores via PBKDF2 — keys are never stored in plaintext
- **Low-S signature normalisation** — prevents the malleability attack that allowed transaction ID mutation in early Bitcoin
- **UUID4 replay nonces** — unique per-signing operation, preventing re-use of captured signatures

### 2. Proof-of-Work with Dynamic Difficulty
- Difficulty expressed as **leading zero hex digits** required in the SHA-256 hash
- **Difficulty adjustment** every 10 blocks — increases if blocks arrive faster than 10s, decreases if slower (minimum difficulty 1)
- Mirrors Bitcoin's 2-week difficulty adjustment but simplified for educational context

### 3. Merkle Tree for Transaction Integrity
- Any transaction modification changes the leaf hash, which bubbles up to change the root
- Changing the Merkle root changes the block hash, which breaks the `previous_hash` of the next block — making tampering immediately detectable across the entire chain
- Empty block handled by hashing an empty string

### 4. Tamper Detection Demo
- `POST /api/tamper/<index>` injects a fake transaction into a block **without recomputing the hash**
- `is_valid_chain()` immediately returns `False` because the stored hash no longer matches the block content
- `POST /api/chain/restore` resets to a clean genesis state — great for live demos

### 5. Smart Contract Event Indexing
- Three indexed events (`TransactionSubmitted`, `TransactionApproved`, `TransactionRejected`) enable efficient on-chain queries
- Python `ContractInterface` wraps `get_logs()` calls, returning plain dicts for easy serialisation

### 6. 5-Stage GitHub Actions CI Pipeline
- **Lint** (Ruff) → **Security** (Bandit) → **Dependency CVE** (pip-audit) → **Solidity Compile** (Hardhat) → **Test + Coverage** (pytest ≥80%)
- Concurrent cancellation of in-progress runs for the same branch/PR
- Coverage HTML report uploaded as a build artifact on every run

---

## 🔒 Security Design

| Attack Vector | Mitigation |
|---|---|
| Private key theft | AES-256-CBC encrypted PEM files, `0o600` POSIX permissions |
| Transaction forgery | ECDSA-SHA256 digital signatures required |
| Replay attacks | UUID4 nonce embedded in every signed message |
| Signature malleability | Low-S normalisation (BIP-62 convention), high-S signatures rejected |
| Block tampering | SHA-256 hash chain — any change propagates forward, breaking all subsequent hashes |
| Double spending | PoW consensus — attacker must redo more work than honest chain |
| Solidity reentrancy | Funds reserved before event emission in `submitTransaction` |
| Address injection | Regex validation gate on all address inputs (`0x[0-9a-fA-F]{40}`) |
| Dependency CVEs | pip-audit scans `requirements.txt` on every CI run |
| Code vulnerabilities | Bandit static analysis on every CI run (medium+high severity) |
| Passphrase leakage | Passphrase read from env var on demand, never cached as module-level global |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.13+
- Node.js 22+
- (Optional) Ganache for smart contract deployment

### 1. Clone and Install Python Dependencies

```bash
git clone https://github.com/GojoV339/secure-blockchain-financial-txn-system.git
cd secure-blockchain-financial-txn-system

# Install with pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Or with uv (faster)
uv sync
```

### 2. Configure Environment

```bash
cp .env.example .env   # or create manually
```

Edit `.env`:
```env
WALLET_ENCRYPTION_PASSPHRASE=your-strong-passphrase-here
DATASET_PATH=datasets/Eth_Txs.csv
KEYSTORE_PATH=keystore
LOG_LEVEL=INFO
```

### 3. Install Node.js Dependencies (for Smart Contract)

```bash
npm install
npx hardhat compile        # compile TransactionContract.sol
```

### 4. Deploy Smart Contract (Optional — requires Ganache)

```bash
# Start Ganache on port 7545, then:
npx hardhat run scripts/deploy.js --network ganache
# Writes deployment.json with contract address
```

### 5. Run the Flask API + Block Explorer

```bash
flask --app api/app.py run --debug
# Open http://127.0.0.1:5000 for the Block Explorer
```

### 6. Run the Test Suite

```bash
python -m pytest tests/ -v --cov=wallet --cov=blockchain --cov=chain --cov=api --cov-report=term-missing
```

---

## 🌍 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `WALLET_ENCRYPTION_PASSPHRASE` | **Required** | AES passphrase for private key encryption |
| `DATASET_PATH` | `datasets/Eth_Txs.csv` | Path to the Ethereum transactions CSV |
| `KEYSTORE_PATH` | `keystore` | Directory for PEM key files |
| `LOG_LEVEL` | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`) |
| `GANACHE_URL` | `http://127.0.0.1:7545` | Ganache JSON-RPC endpoint |

---

## 📡 API Reference

All endpoints are under the `/api` prefix. The root `/` serves the Block Explorer SPA.

### Blocks

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/blocks` | List all blocks — `{"blocks": [...], "count": N}` |
| `GET` | `/api/blocks/<index>` | Get block by zero-based index — 404 if out of range |

### Transactions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/transactions/pending` | All mempool transactions — `{"transactions": [...], "count": N}` |
| `POST` | `/api/transactions/submit` | Submit a new transaction — body: `{"sender","receiver","amount","fee"}` |

### Chain

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/chain/stats` | Live stats — height, total_transactions, difficulty, pending_transactions, is_valid |
| `GET` | `/api/chain/validate` | `{"valid": true/false, "height": N}` |
| `POST` | `/api/mine` | Mine pending transactions — body: `{"miner_address": "0x..."}` |

### Tamper Detection (Educational Demo)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/tamper/<index>` | Inject fake transaction into block `index` without updating hash |
| `POST` | `/api/chain/restore` | Reset chain to clean genesis-only state |

### Example: Full Transaction Lifecycle

```bash
# 1. Submit a transaction
curl -X POST http://localhost:5000/api/transactions/submit \
  -H "Content-Type: application/json" \
  -d '{"sender":"0xAbc...","receiver":"0xDef...","amount":1.5,"fee":0.001}'

# 2. Mine it into a block
curl -X POST http://localhost:5000/api/mine \
  -H "Content-Type: application/json" \
  -d '{"miner_address":"0xMiner..."}'

# 3. View chain stats
curl http://localhost:5000/api/chain/stats

# 4. Demonstrate tamper detection
curl -X POST http://localhost:5000/api/tamper/1
curl http://localhost:5000/api/chain/validate   # returns {"valid": false}

# 5. Restore clean state
curl -X POST http://localhost:5000/api/chain/restore
```

---

## 📜 Smart Contract

### `TransactionContract.sol` — Key Functions

| Function | Access | Description |
|---|---|---|
| `fundWallet(address wallet)` | `external payable` | Credit a wallet's internal ledger |
| `submitTransaction(receiver, value, txFee)` | `external` | Reserve funds, create Pending record |
| `approveTransaction(txHash)` | `onlyOwner` | Credit receiver, fee stays in contract |
| `rejectTransaction(txHash, reason)` | `onlyOwner` | Full refund to sender, reason stored on-chain |
| `getTransaction(txHash)` | `view` | Retrieve full TxRecord struct |
| `getBalance(wallet)` | `view` | Ledger balance in wei |
| `getTxCount()` | `view` | Total submitted transactions |
| `getTxHashAt(index)` | `view` | Transaction hash by submission order |

### Events

| Event | Indexed Fields | Description |
|---|---|---|
| `TransactionSubmitted` | txHash, sender, receiver | Emitted on every `submitTransaction` call |
| `TransactionApproved` | txHash, sender, receiver | Emitted on approval |
| `TransactionRejected` | txHash, sender | Emitted on rejection with reason |
| `WalletFunded` | wallet | Emitted on `fundWallet` |

### Security Properties
- **No reentrancy** — balance deducted before event emission
- **Solidity 0.8.x** — arithmetic overflow reverts automatically
- **Owner-gated** approval/rejection via `onlyOwner` modifier
- **Unique tx hashes** via `keccak256(sender‖receiver‖value‖fee‖timestamp‖blockNumber‖txCount)`

---

## 🧪 Testing & CI/CD

### Test Suite (13 modules)

| Test File | What it tests |
|---|---|
| `test_address_loader.py` | CSV loading, address validation, error cases |
| `test_key_manager.py` | Key generation, encryption, save/load, batch generation |
| `test_signer.py` | Signing, verification, replay protection, malleability rejection |
| `test_block.py` | Block hashing, determinism, serialisation |
| `test_blockchain.py` | Block addition validation, chain integrity |
| `test_merkle.py` | Merkle root computation, odd-length handling |
| `test_mempool.py` | Add/remove/select transactions, overflow protection |
| `test_consensus.py` | PoW mining, difficulty validation, adjustment |
| `test_node.py` | Mining, broadcast, sync, Nakamoto consensus |
| `test_api.py` | Flask route integration tests |
| `test_contract.py` | ContractInterface unit tests (mocked web3) |
| `conftest.py` | Shared fixtures (tmp keystores, sample addresses, key pairs) |

### CI Pipeline (5 stages, GitHub Actions)

```
Push/PR to main
      │
      ├── [1] Ruff Lint & Format ──────────────────────────────────┐
      │                                                             │
      ├── [2] Bandit Security Scan ──────────────────────────────── All pass
      │                                                             │
      ├── [3] pip-audit CVE Check ──────────────────────────────── ▼
      │                                                     [5] pytest + Coverage
      └── [4] Hardhat Compile ────────────────────────────── (≥80% required)
                                                                    │
                                                         Upload htmlcov/ artifact
```

---

## 📁 Project Structure

```
Block_Chain_Project/
│
├── wallet/                        # Phase 1-2: Cryptographic identity
│   ├── config.py                  # .env loading, logging factory
│   ├── exceptions.py              # Domain-specific exception hierarchy
│   ├── address_loader.py          # CSV → validated Ethereum addresses
│   ├── key_manager.py             # ECDSA key gen, encrypted persistence
│   └── signer.py                  # ECDSA-SHA256 sign + verify
│
├── chain/                         # Phase 4-5: Raw blockchain mechanics
│   ├── block.py                   # Block dataclass + SHA-256 hashing
│   ├── merkle.py                  # Binary Merkle tree
│   ├── mempool.py                 # FIFO unconfirmed transaction pool
│   ├── blockchain.py              # Ordered chain + validation
│   ├── consensus.py               # Proof-of-Work + difficulty adjustment
│   └── node.py                    # P2P node (mine, broadcast, sync)
│
├── blockchain/                    # Phase 3: Smart contract Python wrapper
│   └── contract.py                # ContractInterface (web3.py)
│
├── api/                           # Phase 6: REST API + Block Explorer
│   ├── app.py                     # Flask factory, blueprint registration
│   ├── state.py                   # Global Node singleton
│   ├── routes/
│   │   ├── blocks.py              # GET /api/blocks, /api/blocks/<index>
│   │   ├── transactions.py        # GET /api/transactions/pending, POST /api/transactions/submit
│   │   ├── chain.py               # GET /api/chain/stats|validate, POST /api/mine
│   │   └── tamper.py              # POST /api/tamper/<index>, /api/chain/restore
│   └── static/
│       └── index.html             # Block Explorer SPA
│
├── contracts/
│   └── TransactionContract.sol    # Solidity smart contract
│
├── scripts/
│   └── deploy.js                  # Hardhat deploy script → deployment.json
│
├── tests/                         # 13 pytest modules, ≥80% coverage
│   ├── conftest.py
│   ├── test_address_loader.py
│   ├── test_key_manager.py
│   ├── test_signer.py
│   ├── test_block.py
│   ├── test_blockchain.py
│   ├── test_merkle.py
│   ├── test_mempool.py
│   ├── test_consensus.py
│   ├── test_node.py
│   ├── test_api.py
│   └── test_contract.py
│
├── datasets/
│   └── Eth_Txs.csv                # Real Ethereum transaction dataset
│
├── .github/workflows/
│   └── ci.yml                     # 5-stage GitHub Actions CI
│
├── hardhat.config.js              # Solidity compiler + network config
├── pyproject.toml                 # Python project config (Ruff, pytest, coverage)
├── requirements.txt               # Production dependencies
├── requirements-dev.txt           # Dev/test tooling
├── .env                           # Local secrets (not committed)
└── graph.html                     # Interactive architecture dependency graph
```

---

## 🎤 Interview Q&A: Concepts Demonstrated

### "What is Proof-of-Work and how did you implement it?"
> PoW is a consensus mechanism requiring miners to find a nonce such that the block's SHA-256 hash begins with a configurable number of leading zero hex digits (the difficulty). My implementation in `chain/consensus.py` iterates the nonce from 0, recomputing the hash each time, until the target prefix is met. This makes block production computationally expensive while verification is trivial (one hash check). I also implemented dynamic difficulty adjustment every 10 blocks, mirroring Bitcoin's algorithm.

### "Why secp256k1 instead of other curves?"
> secp256k1 is the elliptic curve used by both Bitcoin and Ethereum. It has well-studied security properties, efficient computation, and wide tooling support. By using the same curve, key pairs generated by this system are directly compatible with real Ethereum wallets, which is important for a financial transaction system.

### "How do you prevent replay attacks?"
> Every signing operation in `wallet/signer.py` requires a UUID4 nonce. The nonce is embedded into the canonical JSON message before signing, so a captured `(signature, nonce)` pair is valid only for that exact combination. If an attacker replays the signature with a different nonce, verification fails because the signed message hash won't match. The API layer is responsible for tracking used nonces (per Phase 6 documentation).

### "What is signature malleability and how do you handle it?"
> ECDSA has a mathematical property: both `(r, s)` and `(r, N-s)` are valid signatures for the same message, where N is the curve order. An attacker could change the `s` value to produce a different valid signature, which changes the transaction ID (txid) — this was exploited in the MtGox hack. My signer enforces low-S normalisation: after signing, if `s > N/2`, it replaces `s` with `N-s`. During verification, any signature with a high-S value is explicitly rejected, following Bitcoin BIP-62.

### "How does the Merkle tree help with transaction integrity?"
> A Merkle tree hashes individual transactions into leaf nodes, then pairs them up and hashes again, until a single root hash remains. This root is included in the block hash. If any transaction changes, its leaf hash changes, propagating up to change the root, which changes the block hash, which breaks `previous_hash` of every subsequent block. This makes it impossible to silently modify a historical transaction without invalidating the entire chain from that point forward.

### "What is the Nakamoto longest-chain rule?"
> When two nodes have different chains (e.g. after a network partition), Nakamoto consensus says: adopt whichever chain is longest AND valid. My `Node.sync_chain()` checks `len(peer_chain) > self.blockchain.height() and peer.blockchain.is_valid_chain()` before replacing the local chain. This ensures nodes always converge on the chain representing the most cumulative PoW, making 51% attacks the only way to rewrite history.

### "How does the smart contract prevent double spending?"
> In `submitTransaction`, the sender's balance is deducted (`balances[msg.sender] -= total`) **before** storing the transaction record or emitting any event. This means the funds are reserved atomically. A second `submitTransaction` call will fail the `require(balances[msg.sender] >= total)` check because the balance was already reduced. The Solidity 0.8.x overflow protection also ensures no arithmetic manipulation can create phantom balances.

### "How is the CI pipeline structured?"
> Five parallel/sequential GitHub Actions jobs: (1) Ruff linting — enforces code style and import ordering; (2) Bandit security scan — flags medium and high severity Python security issues; (3) pip-audit — checks all production dependencies against the CVE database; (4) Hardhat compile — validates the Solidity contract compiles cleanly; (5) pytest with coverage — runs all 13 test modules, fails the build if coverage drops below 80%. Jobs 1-3 must pass before job 5 runs; job 4 runs in parallel since it has no Python dependencies.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for full text.

---

*Built as a Semester 6 Blockchain Technology course project demonstrating production-grade blockchain architecture from cryptographic primitives to smart contracts and REST APIs.*
