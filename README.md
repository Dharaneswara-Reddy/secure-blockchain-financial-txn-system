# Secure Blockchain Financial Transaction System

> A production-grade, ground-up implementation of a blockchain financial transaction network — from raw ECDSA cryptographic primitives and SHA-256 Proof-of-Work to a Solidity smart contract, a Flask REST API, and a live browser-based Block Explorer. Built entirely in Python 3.13 and Solidity 0.8.20, with a 5-stage GitHub Actions CI/CD pipeline enforcing code quality, security audits, and ≥80% test coverage.

---

## Abstract

The proliferation of decentralized finance (DeFi) has created an urgent demand for engineers who understand blockchain systems not merely as black-box libraries, but as a composition of precisely engineered cryptographic, consensus, and networking primitives. Existing educational platforms and tutorials provide high-level abstractions that obscure the security-critical design decisions underlying production blockchain networks such as Bitcoin and Ethereum.

This project presents a full-stack blockchain financial transaction system constructed from first principles. The system implements the complete transaction lifecycle: cryptographic wallet identity generation using ECDSA on the secp256k1 elliptic curve with AES-256-CBC encrypted keystores; transaction signing with replay-attack protection via UUID4 nonces and signature malleability defense via BIP-62 low-S normalization; a custom blockchain engine featuring SHA-256 Proof-of-Work with dynamic difficulty adjustment, binary Merkle trees for transaction integrity, and a FIFO mempool; a simulated peer-to-peer network implementing Nakamoto longest-chain consensus; an Ethereum smart contract (`TransactionContract.sol`) governing on-chain fund management with atomic double-spend prevention; a Flask REST API exposing the full chain lifecycle; and a real-time browser Block Explorer SPA. The system is validated by 13 pytest modules with ≥80% coverage enforced in CI, and is accompanied by static security analysis (Bandit), dependency CVE auditing (pip-audit), and Solidity compilation verification.

This repository is intended to serve as both a complete reference implementation and a research artifact for understanding the engineering tradeoffs in distributed ledger design.

---

## Introduction

### Domain Background

Blockchain technology underpins the most significant innovations in decentralized finance, supply chain integrity, digital identity, and trustless computation. At its core, a blockchain is an append-only distributed ledger maintained by a peer-to-peer network without a central authority. Each participant in the network holds an identical copy of the ledger, and consensus on the canonical state is achieved not through trust but through cryptographic proof.

The three foundational problems that blockchain solves are:

1. **The Double-Spending Problem**: How can a digital token be spent by exactly one party when digital data can be copied freely? Traditional systems solve this via central banks or payment processors. Blockchain solves it via consensus — an expenditure is only valid if the majority of the network agrees it occurred.

2. **The Byzantine Generals Problem**: How can distributed nodes reach agreement when some nodes may be faulty or malicious? Bitcoin's Proof-of-Work provides a probabilistic solution where honest behavior is economically incentivized.

3. **Trustless Transaction Finality**: How can a sender prove they authorized a transaction without revealing their identity or secrets? ECDSA digital signatures allow anyone to verify authorization without the sender revealing their private key.

### Limitations of Existing Educational Systems

Existing blockchain tutorials fall into two failure modes. The first provides high-level Python implementations using simple SHA-256 hash chains without addressing the security attack surface: replay attacks, signature malleability, deterministic serialization pitfalls, or reentrancy in smart contracts. The second jumps directly to Ethereum tooling (Hardhat, web3.js, ethers.js) without ever implementing the primitives that make the system secure.

This project deliberately bridges that gap by implementing every security-critical component from first principles while still integrating with real-world tooling (Hardhat, Ganache, web3.py).

### Why This Project Was Developed

This system was developed as a Semester 6 Blockchain Technology course project with the explicit goal of demonstrating end-to-end blockchain competency. The engineering objective was not to build a toy chain, but to make every design decision that a production engineer would make: encrypted keystores, BIP-62 malleability protection, deterministic JSON canonicalization, atomic fund reservation in the smart contract, and a comprehensive CI/CD pipeline.

---

## Objectives

### Primary Goals
- Build a fully functional blockchain from cryptographic primitives without relying on blockchain frameworks
- Demonstrate the complete transaction lifecycle from identity creation to on-chain settlement
- Provide a live, interactive Block Explorer for visual verification of chain state

### Technical Goals
- Implement ECDSA key management on secp256k1 with AES-256-CBC encrypted persistence
- Achieve SHA-256 Proof-of-Work with dynamic difficulty adjustment targeting 10-second block times
- Build a binary Merkle tree providing O(log n) transaction integrity verification
- Implement BIP-62 low-S signature normalization and UUID4 replay protection
- Deploy a Solidity smart contract with atomic double-spend prevention

### Engineering Goals
- Maintain ≥80% test coverage across all Python modules, enforced in CI
- Pass Bandit security scanning (medium+high severity) and pip-audit CVE scanning on every commit
- Structure the codebase with strict separation of concerns across six distinct layers
- Implement a Flask application factory pattern with Blueprint-based routing for testability

### Research Goals
- Serve as a reference implementation for understanding the security design of Ethereum-compatible wallet systems
- Document the precise attack vectors (replay, malleability, reentrancy, double-spend) and their mitigations

---

## Key Features

### 1. secp256k1 ECDSA Wallet Identity System
Full key pair generation using the `cryptography` library's `ec.SECP256K1()` curve — the exact curve used by Bitcoin and Ethereum. Private keys are encrypted at rest using `BestAvailableEncryption` (AES-256-CBC + PBKDF2-HMAC), serialized in PKCS8 PEM format, and written with POSIX `0o600` permissions. Batch generation from a real Ethereum transaction CSV is idempotent — existing keys are skipped.

### 2. BIP-62 Signature Malleability Defense
Every ECDSA signature is normalized to low-S form before output: if `s > N/2` (where N is the secp256k1 curve order), the signer replaces `s` with `N - s`. The verifier rejects any signature with `s > N/2` with a `VerificationError`. This follows Bitcoin BIP-62 and prevents the transaction malleability attack exploited in the Mt. Gox exchange hack.

### 3. UUID4 Replay Attack Protection
Each signing operation requires a caller-supplied nonce (via `create_nonce()` backed by `os.urandom()`). The nonce is embedded in the canonical JSON payload before hashing and signing, making the resulting signature mathematically bound to that specific nonce. Re-submitting a captured `(signature, message)` pair with a different nonce fails cryptographic verification.

### 4. Deterministic Canonical JSON Serialization
All data structures serialized for hashing (block fields, transaction payloads) use `json.dumps(data, sort_keys=True, separators=(",", ":"))`. This eliminates hash inconsistencies caused by Python's non-deterministic dict ordering across interpreter versions, preventing hash-based integrity failures in distributed environments.

### 5. SHA-256 Proof-of-Work with Dynamic Difficulty Adjustment
The mining algorithm increments a nonce until the block's SHA-256 hash starts with `difficulty` leading zero hex digits. Difficulty is adjusted every 10 blocks: if the last 10 blocks arrived faster than the target window, difficulty increases by 1; if slower, it decreases by 1 (minimum 1). This mirrors Bitcoin's 2016-block retargeting algorithm in a simplified form.

### 6. Binary Merkle Tree Transaction Integrity
Transactions within a block are committed to via a binary Merkle tree. Each transaction is individually SHA-256 hashed to produce a leaf. Leaves are pairwise-hashed up to a single root (odd-length levels duplicate the last leaf). The Merkle root is embedded in the block hash, meaning any transaction modification changes the root, which changes the block hash, which invalidates all subsequent blocks.

### 7. Nakamoto Longest-Valid-Chain Consensus
Each `Node` maintains a peer list and broadcasts newly mined blocks via direct method invocation. `receive_block()` validates the PoW proof before accepting. On chain divergence, `sync_chain()` replaces the local chain only if the peer chain is strictly longer AND passes `is_valid_chain()` — implementing the canonical Nakamoto consensus rule.

### 8. Solidity Smart Contract with Atomic Fund Management
`TransactionContract.sol` manages an internal ETH ledger on a local Ethereum network. The critical security invariant in `submitTransaction()` is that funds are debited (`balances[msg.sender] -= total`) **before** any state writes or event emissions, preventing reentrancy attacks. On rejection, funds are fully refunded including the fee; on approval, fees remain in the contract as a miner reward simulation.

### 9. Tamper-Evident Chain Demonstration
`POST /api/tamper/<index>` injects a fake transaction into a mined block without recomputing its hash. The response includes the stored hash, the recomputed hash, and the result of `is_valid_chain()` — demonstrating in real-time that the stored and computed hashes diverge, proving why blockchain data cannot be secretly altered.

### 10. 5-Stage CI/CD Pipeline
Every push and PR to `main` triggers five GitHub Actions jobs: Ruff linting, Bandit security scanning, pip-audit CVE scanning, Hardhat Solidity compilation, and pytest with ≥80% coverage enforcement. The test job uploads an HTML coverage report as a build artifact. Concurrent runs for the same branch/PR are automatically cancelled.

---

## System Architecture

### Architectural Pattern: Layered Hexagonal Architecture

The system is organized into six strictly separated layers, each with a single responsibility and well-defined interfaces:

```
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 6: Presentation Layer                                         │
│  api/static/index.html — Browser SPA (ChainView Block Explorer)     │
├──────────────────────────────────────────────────────────────────────┤
│  Layer 5: API Gateway Layer                                          │
│  api/ — Flask REST API (4 Blueprints, Application Factory)          │
├──────────────────────────────────────────────────────────────────────┤
│  Layer 4: Network / Consensus Layer                                  │
│  chain/node.py — P2P Node, Nakamoto Consensus, Mining Orchestration │
├──────────────────────────────────────────────────────────────────────┤
│  Layer 3: Blockchain Engine Layer                                    │
│  chain/ — Block, Merkle, Mempool, Blockchain, Consensus (PoW)       │
├──────────────────────────────────────────────────────────────────────┤
│  Layer 2: Smart Contract Layer                                       │
│  blockchain/contract.py + contracts/TransactionContract.sol         │
├──────────────────────────────────────────────────────────────────────┤
│  Layer 1: Cryptographic Identity Layer                               │
│  wallet/ — Config, Exceptions, AddressLoader, KeyManager, Signer    │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Interaction Map

```
                    ┌──────────────┐
                    │   Browser    │
                    │  (ChainView) │
                    └──────┬───────┘
                  HTTP     │  polling every 3s
                    ┌──────▼───────┐
                    │  Flask API   │
                    │  (api/)      │
                    └──────┬───────┘
               get_node()  │
                    ┌──────▼───────┐
                    │   Node       │◄──── peer.receive_block()
                    │ (chain/node) │────► peer._broadcast()
                    └──┬─────┬─────┘
            Blockchain │     │ Consensus
               ┌───────┘     └──────────┐
       ┌───────▼───────┐    ┌──────────▼──────┐
       │  Blockchain   │    │   consensus.py   │
       │  + Mempool    │    │   (PoW miner)    │
       └───────┬───────┘    └─────────────────┘
               │ chain[]
       ┌───────▼───────┐
       │    Block      │◄─── merkle.build_merkle_tree()
       │  (SHA-256)    │
       └───────────────┘

  wallet/ (identity layer — used independently)
  ┌─────────────┐   ┌───────────┐   ┌──────────┐
  │ AddressLoad │──►│ KeyManager│──►│  Signer  │
  │  (CSV→addr) │   │ (ECDSA)   │   │(sign/vrfy)│
  └─────────────┘   └───────────┘   └──────────┘

  blockchain/ (smart contract layer — used independently)
  ┌──────────────────┐   JSON-RPC   ┌──────────┐
  │ ContractInterface│─────────────►│  Ganache  │
  │  (web3.py wrap)  │             │ /Hardhat  │
  └──────────────────┘             └──────────┘
```

### Design Philosophy

**Fail-fast over silent degradation**: `get_encryption_passphrase()` raises `KeyError` immediately if the env var is absent. The API returns structured JSON errors with appropriate HTTP codes rather than leaking stack traces.

**Immutability by convention**: Block objects compute their hash in `__post_init__` and the hash is never mutated during normal operation. The tamper endpoint intentionally violates this to demonstrate the detection mechanism.

**Single validation gate**: `validate_address()` in `address_loader.py` is the only place in the entire codebase where Ethereum address format is checked. All other modules call this function rather than implementing independent regex checks.

**Factory pattern for testability**: `create_app()` (Flask factory) and `get_node()` / `reset_node()` (Node singleton) enable isolated test instances without shared state between test functions.

---

## Technology Stack

| Category | Technology | Version | Purpose |
|---|---|---|---|
| **Core Language** | Python | 3.13 | Primary implementation language |
| **Web Framework** | Flask | ≥3.1.0 | REST API server |
| **Cryptography** | cryptography | ≥44.0.2 | ECDSA (secp256k1), AES-256-CBC, PBKDF2 |
| **Blockchain Client** | web3.py | ≥7.14.1 | Ethereum JSON-RPC interface |
| **Data Processing** | pandas | ≥2.3.3 | CSV loading and address extraction |
| **ML (dependency)** | scikit-learn | ≥1.8.0 | Data analysis in experiment notebook |
| **Configuration** | python-dotenv | ≥1.1.0 | `.env` file loading |
| **Smart Contract** | Solidity | 0.8.20 | On-chain transaction contract |
| **Contract Runtime** | Hardhat | ^2.22.18 | Compile, deploy, local Ethereum node |
| **Contract Library** | ethers.js | ^6.13.4 | Hardhat deployment scripting |
| **Local Ethereum** | Ganache | — | Local testnet (port 7545) |
| **Linter** | Ruff | ≥0.11.2 | Python linting + formatting |
| **Security Scanner** | Bandit | ≥1.9.0 | Static security analysis |
| **CVE Auditor** | pip-audit | ≥2.10.0 | Dependency vulnerability scanning |
| **Test Framework** | pytest | ≥9.0.2 | Unit and integration testing |
| **Coverage** | pytest-cov | ≥7.1.0 | Code coverage measurement |
| **CI/CD** | GitHub Actions | — | 5-stage automated pipeline |
| **Node.js** | Node.js | 22 | Hardhat runtime |
| **Frontend** | Vanilla HTML/CSS/JS | — | Block Explorer SPA |
| **Fonts** | Google Fonts (Inter, JetBrains Mono) | — | Dashboard typography |

---

## Repository Structure

```
Block_Chain_Project/
│
├── wallet/                     ← Layer 1: Cryptographic Identity
│   ├── config.py               ← Environment loading, logging factory
│   ├── exceptions.py           ← Domain exception hierarchy (6 classes)
│   ├── address_loader.py       ← CSV → validated Ethereum address set
│   ├── key_manager.py          ← ECDSA keygen, AES-256 persistence
│   └── signer.py               ← ECDSA-SHA256 sign + verify, BIP-62
│
├── chain/                      ← Layer 3: Blockchain Engine
│   ├── block.py                ← Block dataclass, SHA-256 hashing
│   ├── merkle.py               ← Binary Merkle tree
│   ├── mempool.py              ← FIFO unconfirmed transaction pool
│   ├── blockchain.py           ← Ordered chain + integrity validation
│   ├── consensus.py            ← Proof-of-Work + difficulty adjustment
│   └── node.py                 ← P2P node, mining, broadcast, sync
│
├── blockchain/                 ← Layer 2: Smart Contract Interface
│   └── contract.py             ← web3.py wrapper (ContractInterface)
│
├── api/                        ← Layer 5: REST API
│   ├── app.py                  ← Flask application factory
│   ├── state.py                ← Global Node singleton
│   ├── routes/
│   │   ├── blocks.py           ← GET /api/blocks, /api/blocks/<index>
│   │   ├── transactions.py     ← GET/POST /api/transactions/*
│   │   ├── chain.py            ← GET /api/chain/stats|validate, POST /api/mine
│   │   └── tamper.py           ← POST /api/tamper/<index>, /api/chain/restore
│   └── static/
│       └── index.html          ← ChainView Block Explorer SPA (Layer 6)
│
├── contracts/
│   └── TransactionContract.sol ← Solidity smart contract (355 lines)
│
├── scripts/
│   └── deploy.js               ← Hardhat deploy → deployment.json
│
├── datasets/
│   └── Eth_Txs.csv             ← Real Ethereum transaction dataset
│
├── tests/                      ← 13 pytest modules
│   ├── conftest.py             ← Shared fixtures
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
├── .github/workflows/
│   └── ci.yml                  ← 5-stage GitHub Actions pipeline
│
├── hardhat.config.js           ← Solidity compiler + network config
├── package.json                ← Node.js deps (Hardhat, ethers)
├── pyproject.toml              ← Python project config (Ruff, pytest, coverage)
├── requirements.txt            ← Production runtime deps
├── requirements-dev.txt        ← Dev/test tooling
├── .env                        ← Local secrets (gitignored)
├── deployment.json             ← Contract address (generated, gitignored)
├── verify_setup.py             ← Quick web3 connectivity sanity check
├── main.py                     ← Scaffolding entry point (placeholder)
├── experiment.ipynb            ← Data exploration notebook
├── graph.html                  ← Vis.js interactive dependency graph
├── SECURITY.md                 ← Security policy documentation
├── CODEBASE_GUIDE.md           ← File-by-file technical reference
├── PROJECT_NOTES.md            ← Concept deep-dive study guide
└── WALKTHROUGH.md              ← Step-by-step run guide
```

<!-- PART 2 CONTINUES BELOW -->

---

## Core Modules: Deep Technical Analysis

### `wallet/config.py` — Configuration & Secrets Management

**Why it exists**: Centralizing all configuration prevents secret values from being scattered across the codebase and ensures `.env` is loaded exactly once before any module accesses environment variables.

**Key design decisions**:
- `load_dotenv()` is called at module import time, resolving the `.env` file relative to `__file__` (two levels up), making the path resolution robust regardless of the working directory from which Flask is started.
- `get_encryption_passphrase()` is implemented as a **function**, not a module-level variable. If it were a global `str`, any `vars(module)` call, repr of the module, or stack trace could expose the passphrase in logs. Reading it from `os.getenv()` on each call ensures the value is never resident in a Python object that could be inspected.
- `configure_logging(name)` uses `if not logger.handlers` to prevent duplicate handler registration when the same named logger is requested multiple times (a common issue in testing where modules are imported repeatedly).
- **Fail-fast**: A missing `WALLET_ENCRYPTION_PASSPHRASE` raises `KeyError` immediately rather than proceeding with `None` or an empty string, which would silently produce unprotected key files.

### `wallet/exceptions.py` — Domain Exception Hierarchy

**Why it exists**: Broad exception catching (`except Exception`) destroys diagnostic information. A typed exception hierarchy lets callers write precise `except InvalidAddressError` blocks and lets the CI pipeline catch regressions where the wrong exception type propagates.

The six exception classes form a single-inheritance tree rooted at `WalletBaseError(Exception)`:
- `InvalidAddressError` — address regex failure or wrong type (non-string)
- `DatasetLoadError` — file not found, missing columns, empty CSV
- `KeyGenerationError` — CSPRNG or curve parameter failure
- `KeyStorageError` — wrong passphrase (decryption `ValueError`), permission denied, file not found
- `SignatureError` — private key invalid, transaction data not JSON-serializable
- `VerificationError` — signature wrong length, high-S malleability detected, cryptographic verification failure

### `wallet/address_loader.py` — CSV Address Extraction Pipeline

**Why it exists**: Real blockchain systems initialize wallets from existing address databases. This module bridges the gap between the raw Ethereum transaction CSV dataset and the key management system.

**Processing pipeline**:
1. `pd.read_csv(..., usecols=["From", "To"], dtype=str)` — reads only the two necessary columns and forces all values to strings, preventing `NaN` from being typed as `float` and passing the regex.
2. Both columns are unioned into a single `set[str]` of raw candidates.
3. Each candidate is run through `_ETH_ADDRESS_PATTERN.match(candidate)` — the pattern `^0x[0-9a-fA-F]{40}$` is compiled once at module load (not per-call), avoiding ReDoS risk.
4. Valid addresses are stored as **lowercase** — Ethereum addresses are case-insensitive; lowercase is the canonical form for comparison across all modules.
5. Invalid labels (e.g., `"BinanceWallet"`) are logged as `WARNING` rather than silently dropped, providing an audit trail.

**Security note**: The docstring explicitly states that address values are **not** logged at `DEBUG` level to avoid leaking wallet identities in production log aggregators.

### `wallet/key_manager.py` — ECDSA Key Management

**Why it exists**: Cryptographic key material must be generated from a hardware-backed CSPRNG, serialized in a standardized format, protected by symmetric encryption at rest, and accessed with file system permission controls. This module encapsulates all of these responsibilities.

**`generate_key_pair()`**: Calls `ec.generate_private_key(ec.SECP256K1())`. The `cryptography` library sources entropy from the OS CSPRNG (`/dev/urandom` on Linux), ensuring cryptographically secure randomness.

**`serialize_private_key(private_key, passphrase)`**: The `BestAvailableEncryption(passphrase.encode("utf-8"))` backend selects AES-256-CBC with PBKDF2-HMAC key derivation — the strongest algorithm available in the `cryptography` library at runtime. The PKCS8 container format is the PKCS standard for private key storage, ensuring portability.

**`save_keys()`**: After writing the encrypted PEM, `os.chmod(path, 0o600)` is called. This POSIX permission — owner read/write only — prevents other users on multi-user systems from reading key material. The public key is written unencrypted (public keys are not secret).

**`generate_keys_for_addresses(addresses)`**: Checks for `<address>_private.pem` existence before generating. This idempotency guarantee means the function can be safely called on startup without overwriting existing valid keystores.

### `wallet/signer.py` — Transaction Signing & Verification

**Why it exists**: Digital signatures are the mechanism by which the network verifies that a transaction was authorized by the owner of a private key without requiring the owner to reveal that key.

**Constants**:
- `_SECP256K1_ORDER` — the group order N of the secp256k1 curve (a 256-bit prime ~1.16 × 10⁷⁷)
- `_SECP256K1_HALF_ORDER` — N // 2, the threshold for low-S normalization
- `_SIGNATURE_SIZE = 64` — 32 bytes for r + 32 bytes for s in big-endian

**`_build_canonical_message(tx_data, nonce)`**:
Merges `{**tx_data, "__nonce__": nonce}` and serializes with `json.dumps(sort_keys=True, separators=(",", ":"))`. The `"__nonce__"` key is prefixed with double underscores to avoid collision with any legitimate transaction field named `"nonce"`.

**`sign_transaction(tx_data, private_key, nonce)`**:
1. Builds canonical bytes
2. `private_key.sign(message, ec.ECDSA(hashes.SHA256()))` → DER-encoded signature
3. `decode_dss_signature(der)` → `(r, s)` integers
4. `_normalise_low_s(r, s)` → low-S form
5. `r.to_bytes(32, "big") + s.to_bytes(32, "big")` → fixed 64-byte output

The fixed-width raw encoding is deliberately chosen over DER: DER allows variable-length encoding of integers, creating a surface for encoding ambiguity bugs. Fixed 32+32 bytes makes malleability checks O(1) and eliminates length-parsing vulnerabilities.

**`verify_signature(signature, public_key, tx_data, nonce)`**:
1. Length check: `len(signature) != 64` → `VerificationError`
2. Decode `r = int.from_bytes(sig[:32], "big")`, `s = int.from_bytes(sig[32:], "big")`
3. `s > _SECP256K1_HALF_ORDER` → `VerificationError` (BIP-62 enforcement)
4. Rebuild canonical message from `tx_data + nonce`
5. Re-encode to DER via `encode_dss_signature(r, s)` (library requires DER for `verify()`)
6. `public_key.verify(der, message, ec.ECDSA(hashes.SHA256()))` — raises `InvalidSignature` on failure

### `chain/block.py` — Block Data Structure

**Why it exists**: The Block is the atomic unit of the chain. Every security property of the blockchain — tamper evidence, immutability, ordering — flows from the Block's hash including both its content and its backward pointer.

**`__post_init__`** (Python dataclass hook): If `hash` is not supplied at construction time, `compute_hash()` is called immediately. This means every Block instance is in a consistent state from the moment it exists — there is no window where a Block has been constructed but not yet hashed.

**`compute_hash()`**: Serializes `{index, transactions, previous_hash, nonce, timestamp}` with canonical JSON, then returns `hashlib.sha256(data.encode()).hexdigest()`. The inclusion of `timestamp` ensures that two otherwise-identical blocks (same transactions, same nonce, same previous_hash) produce different hashes if mined at different times.

**`GENESIS_PREV_HASH = "0" * 64`**: Sixty zero characters represent the "null pointer" for the genesis block. Using zeros (rather than an empty string or `None`) ensures the genesis block's hash is a valid 64-character hex string, which simplifies downstream validation logic.

### `chain/merkle.py` — Binary Merkle Tree

**Why it exists**: Storing all transaction hashes individually in the block hash would make block verification O(n) in transaction count. The Merkle tree reduces proof size to O(log n), enabling future "light client" implementations to verify transaction inclusion without the full block.

**Algorithm**:
```
Input:  [tx0, tx1, tx2]
Step 0: hash each tx → [h0, h1, h2]
Step 1: odd → duplicate last: [h0, h1, h2, h2]
        pair and hash: [hash(h0+h1), hash(h2+h2)]
Step 2: pair and hash: [hash(hash(h0+h1) + hash(h2+h2))]
Output: single Merkle root
```

**Edge case — empty block**: Returns `hashlib.sha256(b"").hexdigest()` — the SHA-256 of an empty byte string. This is a deterministic, reproducible value for genesis blocks or empty mining rounds.

### `chain/mempool.py` — Unconfirmed Transaction Pool

**Why it exists**: The mempool is the staging area between transaction submission and block confirmation. Without it, the API would need to mine synchronously on every transaction submission, which is impractical given PoW mining times.

**Data structure**: `collections.deque` — chosen specifically because `popleft()` is O(1), making FIFO ordering efficient. A `list` would require O(n) for `pop(0)`.

**`add_transaction(tx)`**: Stamps a `uuid.uuid4()` ID and `time.time()` timestamp onto the transaction dict before appending. This ensures every in-flight transaction has a unique identifier for deduplication and a submission timestamp for ordering.

**`remove_transactions(tx_ids)`**: Converts `tx_ids` to a `set` before filtering, making the lookup O(1) per transaction rather than O(m) where m is the number of IDs being removed.

**Overflow protection**: `max_size` (default 1000) prevents unbounded memory growth. `OverflowError` is raised on `add_transaction` when the pool is full, and the API propagates this as HTTP 503.

### `chain/blockchain.py` — Chain Management

**Why it exists**: The Blockchain manages the ordered list of blocks and enforces the two invariants that make the chain tamper-evident: hash integrity and backward-pointer linkage.

**`add_block(block)`** validates two conditions:
1. `block.previous_hash == self.last_block().hash` — the new block correctly extends the current chain tip
2. `block.hash == block.compute_hash()` — the stored hash matches the recomputed hash (catches pre-tampered blocks)

Returns `False` on failure rather than raising, allowing the caller (`node.py`) to decide whether to attempt chain sync.

**`is_valid_chain()`**: Iterates from index 1 (genesis is always valid by construction). For each block: verifies stored hash matches computed hash, and `previous_hash` matches the preceding block's stored hash. Returns `False` on first violation — this is the function that returns `False` after a tamper attack.

### `chain/consensus.py` — Proof-of-Work Engine

**Why it exists**: PoW makes block production computationally expensive while keeping verification O(1). This asymmetry is what makes the blockchain secure — an attacker would need to outcompute the entire honest network to rewrite history.

**`mine_block(block, difficulty)`**: Sets `prefix = "0" * difficulty` and increments `block.nonce` until `block.compute_hash().startswith(prefix)`. The expected number of hash computations is 16^difficulty (because each hex digit has 1/16 probability of being zero). At difficulty 3, this is ~4,096 iterations on average.

**`adjust_difficulty(chain, current_difficulty)`**:
- Triggers only at `chain.height() % DIFFICULTY_ADJUSTMENT_INTERVAL == 0` (every 10 blocks)
- `elapsed = chain.chain[-1].timestamp - chain.chain[-10].timestamp`
- `expected = DIFFICULTY_ADJUSTMENT_INTERVAL * TARGET_BLOCK_TIME` (10 × 10 = 100 seconds)
- `elapsed < expected / 2` → increase by 1 (blocks arriving too fast)
- `elapsed > expected * 2` → decrease by 1, minimum 1 (blocks arriving too slow)

### `chain/node.py` — P2P Network Node

**Why it exists**: A blockchain without a network is just a local database. The Node wraps the Blockchain with peer management and broadcasting logic, simulating the P2P layer of a real distributed network.

**`mine_pending_transactions(miner_address)`** — the critical orchestration function:
1. `mempool.select_transactions(max_txs=10)` — non-destructive read
2. Prepend coinbase: `{"sender": "NETWORK", "receiver": miner_address, "amount": 50.0, "type": "coinbase"}` — simulates Bitcoin's block subsidy
3. `Block(index=last.index+1, transactions=all_txs, previous_hash=last.hash)`
4. `mine_block(new_block, self.difficulty)` — CPU-intensive PoW
5. `blockchain.add_block(mined_block)` — validates and appends
6. `mempool.remove_transactions([tx["id"] for tx in pending_txs])` — cleans up
7. `adjust_difficulty(blockchain, self.difficulty)` — updates difficulty
8. `_broadcast(mined_block)` — propagates to all peers

**`sync_chain(peer)`** — Nakamoto consensus implementation:
```python
if len(peer.blockchain.chain) > self.blockchain.height():
    if peer.blockchain.is_valid_chain():
        self.blockchain.chain = list(peer.blockchain.chain)
```
The double check (longer AND valid) prevents an attacker from forcing a chain replacement by broadcasting a long but invalid chain.

### `blockchain/contract.py` — Smart Contract Interface

**Why it exists**: The Python blockchain simulation and the Solidity on-chain contract are two independent systems. This module provides a single clean interface between them, abstracting away web3.py's verbose API.

**`load_abi(artifact_path)`**: Reads from `artifacts/contracts/TransactionContract.sol/TransactionContract.json` — the Hardhat-generated artifact. This means the ABI is always in sync with the compiled bytecode, rather than being hardcoded and potentially stale.

**`from_deployment_file(web3)`**: Reads `deployment.json` (generated by `scripts/deploy.js`). This factory method means neither the contract address nor the ABI is hardcoded anywhere in Python source code.

**`.call()` vs `.transact()`**: Read-only functions (`getTransaction`, `getBalance`, `getTxCount`, `getTxHashAt`) use `.call()` — local EVM simulation, no gas, instant. State-changing functions (`fundWallet`, `submitTransaction`, `approveTransaction`, `rejectTransaction`) use `.transact()` — broadcast to network, consumes gas, returns transaction hash, then `w3.eth.wait_for_transaction_receipt()` blocks until mined.

### `contracts/TransactionContract.sol` — On-Chain Smart Contract

**Why it exists**: The Python blockchain simulates consensus without real economic finality. The Solidity contract provides actual Ethereum-level guarantees: EVM execution, cryptographic transaction hashing, immutable event logs, and Solidity 0.8.x overflow protection.

**`TxRecord` struct**:
```solidity
struct TxRecord {
    address sender;
    address receiver;
    uint256 value;       // in wei
    uint256 txFee;       // in wei
    Status status;       // Pending | Approved | Rejected
    uint256 timestamp;
    string rejectReason; // empty unless rejected
}
```

**`submitTransaction` — critical security ordering**:
```solidity
uint256 total = value + txFee;
require(balances[msg.sender] >= total, "Insufficient balance");
balances[msg.sender] -= total;  // ← DEDUCT FIRST
// ... then write state and emit event
```
This ordering prevents reentrancy: even if a malicious contract calls `submitTransaction` recursively before the first call returns, the balance has already been decremented, so the `require` will fail on the recursive call.

**Unique transaction hash generation**:
```solidity
bytes32 txHash = keccak256(abi.encodePacked(
    msg.sender, receiver, value, txFee,
    block.timestamp, block.number, _txCount
));
```
The inclusion of `block.timestamp`, `block.number`, and `_txCount` (a monotonic counter) makes hash collisions computationally infeasible even for identical transactions.

### `api/app.py` — Flask Application Factory

**Why a factory**: The `create_app()` pattern (not a module-level `app = Flask(...)`) allows test suites to create isolated app instances without shared state. Each test function calls `create_app()`, gets a fresh Flask instance with a fresh test client.

**Blueprint registration**:
```python
app.register_blueprint(blocks_bp, url_prefix="/api")
app.register_blueprint(transactions_bp, url_prefix="/api")
app.register_blueprint(chain_bp, url_prefix="/api")
app.register_blueprint(tamper_bp, url_prefix="/api")
```
The `url_prefix="/api"` means all API routes are namespaced under `/api`, while `GET /` serves `static/index.html` — the Block Explorer SPA.

### `api/state.py` — Global Node Singleton

**Why a singleton**: Flask is a synchronous WSGI application. A single-process Flask server processes one request at a time. The `_node: Node | None = None` module-level variable persists across the lifetime of the process, maintaining blockchain state between requests. `reset_node()` sets it to `None`, and the next `get_node()` call lazy-creates a fresh instance — used in tests to guarantee test isolation.

### `api/static/index.html` — ChainView Block Explorer SPA

**Architecture**: A self-contained single-page application in vanilla HTML/CSS/JavaScript with zero external JavaScript dependencies (no React, Vue, or jQuery). All state is fetched from the API and rendered synchronously.

**Polling**: `setInterval(refresh, 3000)` drives a 3-second polling loop calling three endpoints: `/api/chain/stats`, `/api/transactions/pending`, `/api/blocks`. This provides near-real-time updates without WebSocket complexity.

**Visual design**: Dark theme with CSS custom properties for the color palette (`--bg:#07090f`, `--accent:#6366f1`, `--green:#10b981`, `--red:#f43f5e`). JetBrains Mono is used for hash values and addresses; Inter for all other text.

**Tamper visualization**: When `is_valid_chain()` returns `false`, the header badge changes from `"Valid Chain"` (green pulse dot) to `"⚠ Chain Tampered!"` (red). Block cards for tampered blocks get a `.tampered` CSS class that adds a red border and subtle red background.


---

## Workflow Explanations

### Startup Workflow

```
flask --app api/app.py run --debug
          │
          ▼
    api/app.py imported
          │
          ▼
    create_app() called
    ├── Flask(__name__, static_folder="static")
    ├── register blocks_bp, transactions_bp, chain_bp, tamper_bp
    └── return app
          │
          ▼
    First HTTP request arrives
          │
          ▼
    get_node() called (api/state.py)
    ├── _node is None → create Node("api-node", difficulty=3)
    │     ├── Blockchain.__init__()
    │     │     ├── Mempool.__init__() — empty deque
    │     │     └── _create_genesis_block()
    │     │           └── Block(index=0, txs=[], prev="000...0") → compute_hash()
    │     └── peers = []
    └── return _node (cached for all future requests)
```

The genesis block is created exactly once per Flask process lifetime. Its `previous_hash` is `"0" * 64` and it contains no transactions.

### Transaction Submission Workflow

```
POST /api/transactions/submit
  Body: {"sender": "0xAbc...", "receiver": "0xDef...", "amount": 1.5, "fee": 0.001}
          │
          ▼
  routes/transactions.py: submit_transaction()
  ├── validate required fields: {sender, receiver, amount}
  ├── cast types: sender→str, receiver→str, amount→float, fee→float (default 0.001)
  ├── node.blockchain.mempool.add_transaction(tx)
  │     ├── check len(pool) < max_size (1000) → OverflowError if full
  │     ├── stamp tx["id"] = str(uuid4())
  │     ├── stamp tx["submitted_at"] = time.time()
  │     └── deque.append(tx)
  └── return 201 {"tx_id": uuid, "status": "pending"}
```

The dashboard's "Pending TXs" counter increments immediately because the 3-second polling loop calls `/api/chain/stats` which reads `mempool.pending_count()`.

### Mining Workflow

```
POST /api/mine
  Body: {"miner_address": "0xMINER"}
          │
          ▼
  routes/chain.py: mine()
  ├── start = time.time()
  ├── node.mine_pending_transactions("0xMINER")
  │     │
  │     ├── [1] mempool.select_transactions(10) → list of up to 10 pending txs
  │     │
  │     ├── [2] prepend coinbase tx
  │     │     {"sender": "NETWORK", "receiver": "0xMINER", "amount": 50.0}
  │     │
  │     ├── [3] Block(index=last+1, txs=coinbase+pending, previous_hash=last.hash)
  │     │     └── __post_init__: compute_hash() called, hash stored
  │     │
  │     ├── [4] mine_block(block, difficulty=3) [CPU-intensive loop]
  │     │     ├── prefix = "000"
  │     │     ├── nonce = 0
  │     │     └── while not hash.startswith("000"):
  │     │           block.nonce += 1
  │     │           block.hash = block.compute_hash()
  │     │
  │     ├── [5] blockchain.add_block(mined_block)
  │     │     ├── check previous_hash linkage
  │     │     ├── check hash integrity
  │     │     └── chain.append(mined_block)
  │     │
  │     ├── [6] mempool.remove_transactions(pending tx IDs)
  │     │
  │     ├── [7] adjust_difficulty(blockchain, difficulty)
  │     │     └── (only triggers at blocks % 10 == 0)
  │     │
  │     └── [8] _broadcast(mined_block) to all peers
  │           └── peer.receive_block(block, sender=self)
  │
  ├── elapsed = time.time() - start
  └── return 201 {"block": block.to_dict(), "time_seconds": elapsed, "new_difficulty": 3}
```

### Tamper Detection Workflow

```
POST /api/tamper/1
          │
          ▼
  tamper.py: tamper_block(index=1)
  ├── validate: index >= 1 AND index < chain.height()
  ├── block = blockchain.chain[1]
  ├── original_hash = block.hash  (e.g., "000a4b...")
  ├── block.transactions.append(
  │     {"sender": "ATTACKER", "receiver": "ATTACKER", "amount": 999999}
  │   )                            ← MUTATION WITHOUT HASH UPDATE
  └── return {
        "original_hash": "000a4b...",
        "recomputed_hash": "f8e3c1...",    ← completely different
        "stored_hash": "000a4b...",        ← still the old hash
        "hash_mismatch": true,
        "chain_valid": false               ← is_valid_chain() detects it
      }

GET /api/chain/validate
  └── is_valid_chain() scans chain:
        Block #1: stored_hash("000a4b") ≠ compute_hash("f8e3c1") → return False
```

### Smart Contract Deployment & Interaction Workflow

```
[Terminal 1] Start Ganache on port 7545
                    │
[Terminal 2] npx hardhat compile
             → Compiles TransactionContract.sol → Solidity 0.8.20
             → Writes ABI + bytecode to artifacts/
                    │
             npx hardhat run scripts/deploy.js --network ganache
             ├── ethers.getSigners() → deployer account
             ├── ContractFactory.deploy() → deploys bytecode
             ├── contract.waitForDeployment() → blocks until mined
             ├── receipt.blockNumber, receipt.gasUsed → logged
             └── fs.writeFileSync("deployment.json", {address, network, ...})
                    │
[Python]     ContractInterface.from_deployment_file(w3)
             ├── reads deployment.json → contract address
             ├── load_abi(artifact_path) → ABI from Hardhat artifact
             └── w3.eth.contract(address, abi) → contract object
                    │
             iface.fund_wallet("0xAlice...", amount_ether=10.0, sender=deployer)
             ├── w3.to_wei(10.0, "ether")
             ├── contract.functions.fundWallet("0xAlice").transact({value: wei})
             └── w3.eth.wait_for_transaction_receipt(tx_hash)
                    │
             iface.submit_transaction("0xAlice", "0xBob", 1.5, 0.001)
             ├── contract.functions.submitTransaction(receiver, value_wei, fee_wei)
             │   .transact({"from": "0xAlice"})
             └── process_receipt → extract txHash from TransactionSubmitted event
                    │
             iface.approve_transaction(tx_hash, sender=owner)
             └── contract.functions.approveTransaction(tx_hash).transact({"from": owner})
```

---

## API Documentation

### Base URL
`http://127.0.0.1:5000` (local development)

### Endpoints Reference

#### Blocks

| Method | Path | Description | Response |
|---|---|---|---|
| `GET` | `/api/blocks` | All blocks in chain | `{"blocks": [...], "count": N}` |
| `GET` | `/api/blocks/<index>` | Single block by index | Block dict or `404` |

**Block dict schema**:
```json
{
  "index": 1,
  "hash": "000a4b...",
  "previous_hash": "000000...",
  "nonce": 4137,
  "timestamp": 1746677234.182,
  "transactions": [...],
  "tx_count": 3
}
```

#### Transactions

| Method | Path | Description | Response |
|---|---|---|---|
| `GET` | `/api/transactions/pending` | Mempool contents | `{"transactions": [...], "count": N}` |
| `POST` | `/api/transactions/submit` | Add tx to mempool | `201 {"tx_id": "...", "status": "pending"}` |

**Submit request body**:
```json
{
  "sender": "0xdd487c027448d3364355707d91eefadc2dae9f88",
  "receiver": "0x3e1b1fe45cb2040b97cdb3191d4933ad1ff0928d",
  "amount": 1.5,
  "fee": 0.001
}
```

**Error responses**:
- `400` — missing required fields (`sender`, `receiver`, `amount`)
- `503` — mempool full (>1000 pending transactions)

#### Chain

| Method | Path | Description | Response |
|---|---|---|---|
| `GET` | `/api/chain/stats` | Live chain statistics | Stats object |
| `GET` | `/api/chain/validate` | Integrity check | `{"valid": bool, "height": N}` |
| `POST` | `/api/mine` | Mine pending transactions | `201` mined block or `500` |

**Stats response**:
```json
{
  "height": 4,
  "total_transactions": 12,
  "difficulty": 3,
  "pending_transactions": 2,
  "last_hash": "000abc...",
  "last_block_index": 3,
  "is_valid": true
}
```

**Mine request body**:
```json
{ "miner_address": "0xYourAddress..." }
```
`miner_address` is optional — defaults to `0x0000000000000000000000000000000000000001`.

#### Tamper Demonstration

| Method | Path | Description | Response |
|---|---|---|---|
| `POST` | `/api/tamper/<index>` | Inject fake tx into block | Tamper report |
| `POST` | `/api/chain/restore` | Reset to clean genesis | Confirmation |

**Tamper response**:
```json
{
  "message": "Block #1 has been tampered. Chain is now INVALID.",
  "block_index": 1,
  "original_tx_count": 3,
  "new_tx_count": 4,
  "original_hash": "000a4b...",
  "recomputed_hash": "f8e3c1...",
  "stored_hash": "000a4b...",
  "hash_mismatch": true,
  "chain_valid": false
}
```

**Validation and error handling**: All routes return structured JSON errors. The `400` response always includes an `"error"` key with a human-readable message. HTTP status codes follow REST conventions: `200` for reads, `201` for successful creation (mine, submit), `400` for client errors, `404` for not found, `500` for server-side failures, `503` for resource exhaustion.

---

## Configuration System

### Environment Variables

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `WALLET_ENCRYPTION_PASSPHRASE` | `str` | — | **Yes** | AES-256-CBC encryption passphrase for private key files. `KeyError` if unset. |
| `DATASET_PATH` | `str` | `datasets/Eth_Txs.csv` | No | Relative path to Ethereum transaction CSV from project root. |
| `KEYSTORE_PATH` | `str` | `keystore` | No | Directory for encrypted PEM key files. Created if absent. |
| `LOG_LEVEL` | `str` | `INFO` | No | Python logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `GANACHE_URL` | `str` | `http://127.0.0.1:7545` | No | Ganache JSON-RPC endpoint (used by `hardhat.config.js`). |

### Secrets Handling

| Secret | Storage | Gitignored | Access Pattern |
|---|---|---|---|
| Encryption passphrase | `.env` file | Yes (`.gitignore`) | `os.getenv()` on demand, never cached |
| Private keys | `keystore/*.pem` | Yes | `load_private_key()` with passphrase |
| Contract address | `deployment.json` | Recommended | `from_deployment_file()` |

The CI pipeline injects a throwaway passphrase (`ci-test-passphrase-only`) directly in the workflow YAML:
```yaml
echo "WALLET_ENCRYPTION_PASSPHRASE=ci-test-passphrase-only" > .env
```
This never touches a repository secret and ensures the passphrase is scoped to the CI runner's ephemeral environment.

### Ruff Configuration (`pyproject.toml`)

```toml
[tool.ruff]
line-length = 120          # wider than PEP 8's 79 for readability in modern IDEs

[tool.ruff.format]
quote-style = "double"     # consistent with Black
indent-style = "space"
line-ending = "lf"         # Unix line endings

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101"]       # allow assert in tests (Bandit would flag as security risk)
```

### Hardhat Configuration

```javascript
solidity: { version: "0.8.20", optimizer: { enabled: true, runs: 200 } }
networks:
  ganache: { url: process.env.GANACHE_URL || "http://127.0.0.1:7545", chainId: 1337 }
  localhost: { url: "http://127.0.0.1:8545", chainId: 31337 }
```

`runs: 200` is the Solidity optimizer's run count — a value of 200 optimizes for execution cost (assuming the contract will be called 200+ times), which is appropriate for a transaction contract.

---

## CI/CD Pipeline

### Pipeline Architecture

```
Push / PR to main
        │
        ├─────────────┬────────────────┬──────────────────────┐
        ▼             ▼                ▼                      ▼
   [Job 1]       [Job 2]          [Job 3]               [Job 4]
   Ruff Lint    Bandit Scan    pip-audit CVE       Hardhat Compile
   & Format       Python        production          Solidity 0.8.20
                  security      requirements.txt    (no deploy)
        │             │                │
        └─────────────┴────────────────┘
                       │
                       ▼  (all three must pass)
                   [Job 5]
              pytest + Coverage
              ≥80% enforced
              htmlcov/ uploaded
              as artifact
```

### Concurrency Control
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```
If a second push to the same branch occurs while a pipeline is running, the in-progress run is cancelled. This prevents resource waste during rapid iteration.

### Coverage Configuration
```toml
[tool.coverage.run]
source = ["wallet", "blockchain", "chain", "api"]
```
Coverage is measured across all four Python packages. The `--cov-fail-under=80` flag makes the entire CI job fail if coverage drops below 80%, enforced on every commit.

### Job Dependencies
Jobs 1, 2, 3, and 4 run in parallel. Job 5 (`test`) has `needs: [lint, security, dependency-check]` but does **not** depend on `contracts-compile` — Hardhat compilation has no Python dependencies, and the Python tests mock the web3 contract interface rather than requiring a running Ganache.


---

## Frontend Architecture (ChainView Block Explorer)

### Component Structure

The SPA is a single HTML file with no build step and no external JavaScript dependencies. Its structure maps directly to three visual regions:

```
index.html
├── <style>             ← Inline CSS with CSS custom properties
├── #header             ← Chain title + live validity badge
├── #stats-bar          ← 4 live stats (height, txs, difficulty, pending)
├── #layout (grid: 360px | 1fr)
│   ├── .panel (left)   ← Transaction Feed
│   │   ├── .tx-form    ← Submit transaction inputs
│   │   ├── .btn-mine   ← Mine block button
│   │   └── #tx-list    ← Rendered pending transactions
│   └── #explorer-panel (right)
│       ├── #block-list ← Rendered block cards (expandable)
│       └── #tamper-section ← Block index input + Tamper/Restore buttons
└── <script>            ← All JavaScript: API calls, rendering, polling
```

### State Management

State is entirely server-driven. The client holds no local state beyond `_openBlock` (which block card is currently expanded). Every 3 seconds, three API calls refresh all UI regions:

```javascript
function refresh() {
    refreshStats();    // → GET /api/chain/stats
    refreshTxFeed();   // → GET /api/transactions/pending
    refreshBlocks();   // → GET /api/blocks + GET /api/chain/validate
}
setInterval(refresh, 3000);
```

### Validity Visualization

```javascript
if (d.is_valid) {
    badge.className = "status-badge";        // green pulse dot
    txt.textContent = "Valid Chain";
} else {
    badge.className = "status-badge invalid"; // red
    txt.textContent = "⚠ Chain Tampered!";
}
```

Block cards receive `.tampered` class when `!valid.valid && b.index > 0`, applying a red border and red background tint without JavaScript animation — purely CSS class toggling.

### Toast Notification System

```javascript
function toast(msg, ok=true) {
    const t = document.getElementById("toast");
    t.textContent = msg;
    t.className = "show " + (ok ? "ok" : "err");
    clearTimeout(t._tid);
    t._tid = setTimeout(() => t.className = "", 3000);
}
```
The `clearTimeout` on `t._tid` prevents stacked timeouts when multiple toasts are triggered in rapid succession — the timer always resets to 3 seconds from the latest toast.

---

## Database Design

### In-Memory Blockchain Storage

The system uses **no external database**. All state is held in Python objects in the Flask process's memory:

```
Node._node (module-level singleton)
└── blockchain: Blockchain
    ├── chain: list[Block]
    │   └── Block
    │       ├── index: int
    │       ├── transactions: list[dict]
    │       ├── previous_hash: str
    │       ├── timestamp: float
    │       ├── nonce: int
    │       └── hash: str
    └── mempool: Mempool
        └── _pool: deque[dict]
            └── tx dict
                ├── sender: str
                ├── receiver: str
                ├── amount: float
                ├── fee: float
                ├── id: str (UUID4)
                └── submitted_at: float
```

**Persistence**: None. Restarting the Flask process resets the chain to genesis. The `POST /api/chain/restore` endpoint provides a programmatic reset without restarting.

**Rationale**: For an educational blockchain implementation, in-memory storage dramatically simplifies the architecture while preserving all the interesting cryptographic and consensus behaviors. Adding persistent storage (SQLite, PostgreSQL) would be a natural production enhancement.

### On-Chain Storage (Ethereum / Ganache)

The Solidity contract uses Ethereum's native storage:

```solidity
mapping(address => uint256) public balances;        // wallet → wei balance
mapping(bytes32 => TxRecord) private _transactions; // txHash → full record
bytes32[] private _txHashes;                        // ordered submission list
address public owner;
uint256 private _txCount;                           // monotonic counter
```

Ethereum storage slots are 32 bytes each. The `TxRecord` struct occupies multiple storage slots. `string rejectReason` is dynamically sized and stored in a separate slot with its length header.

---

## Testing Architecture

### Test Module Inventory

| Test File | Module Tested | Key Scenarios |
|---|---|---|
| `test_address_loader.py` | `wallet/address_loader.py` | Valid/invalid addresses, CSV loading, missing file, missing columns, empty CSV, non-string input |
| `test_key_manager.py` | `wallet/key_manager.py` | Key generation, serialization, save/load round-trip, wrong passphrase rejection, batch generation idempotency |
| `test_signer.py` | `wallet/signer.py` | Sign/verify happy path, nonce mismatch rejection, wrong public key rejection, high-S malleability rejection, 64-byte format enforcement |
| `test_block.py` | `chain/block.py` | Hash computation, determinism (same inputs = same hash every time), genesis sentinel, `to_dict()` completeness |
| `test_blockchain.py` | `chain/blockchain.py` | Add valid block, reject wrong `previous_hash`, reject tampered hash, `is_valid_chain()` true/false |
| `test_merkle.py` | `chain/merkle.py` | Empty list, single tx, even count, odd count (duplication), different txs produce different roots |
| `test_mempool.py` | `chain/mempool.py` | Add, select (FIFO order), remove, overflow `OverflowError`, `pending_count()`, `get_all()` |
| `test_consensus.py` | `chain/consensus.py` | PoW prefix check, `validate_proof()` true/false, `adjust_difficulty()` increase/decrease/unchanged |
| `test_node.py` | `chain/node.py` | Mine with coinbase, broadcast to peer, `receive_block()` acceptance, `sync_chain()` Nakamoto rule |
| `test_api.py` | `api/` | All Flask routes, 400/404/503 error paths, mining endpoint, tamper + restore cycle |
| `test_contract.py` | `blockchain/contract.py` | All `ContractInterface` methods with mocked web3.py |
| `conftest.py` | (shared fixtures) | `tmp_keystore`, `sample_addresses`, `sample_key_pair`, `sample_tx_data`, `sample_csv`, `test_passphrase` |

### Fixture Design (`conftest.py`)

```python
@pytest.fixture()
def tmp_keystore(tmp_path: Path) -> Path:
    """Pytest tmp_path is unique per test — ensures no cross-test keystore pollution."""
    keystore_dir = tmp_path / "keystore"
    keystore_dir.mkdir()
    return keystore_dir

@pytest.fixture()
def sample_key_pair():
    """Fresh ECDSA key pair per test — never reuses keys across tests."""
    from wallet.key_manager import generate_key_pair
    return generate_key_pair()
```

The `tmp_path` fixture (built-in pytest) provides a unique temporary directory per test invocation, automatically cleaned up after the test session. This prevents key files from one test leaking into another.

---

## Security Analysis

### Threat Model

| Threat | Attack | Mitigation | Implementation |
|---|---|---|---|
| Private key theft | Filesystem read | AES-256-CBC encryption + `0o600` permissions | `key_manager.save_keys()` |
| Transaction forgery | Submit without private key | ECDSA-SHA256 signature required | `signer.verify_signature()` |
| Replay attack | Resubmit captured signed tx | UUID4 nonce in signed payload | `signer.create_nonce()`, `_build_canonical_message()` |
| Signature malleability | Flip s to N-s | BIP-62 low-S normalization, high-S rejection | `_normalise_low_s()`, `verify_signature()` |
| Serialization attack | Reorder JSON keys to get same signature | `sort_keys=True, separators=(",",":")` | `_build_canonical_message()` |
| Block tampering | Modify transaction in historical block | SHA-256 hash chain invalidation | `is_valid_chain()` |
| Chain rewrite | Mine alternative longer chain | Nakamoto PoW requirement | `sync_chain()` with `is_valid_chain()` |
| Double spending (smart contract) | Call `submitTransaction` twice before balance updates | Balance deducted before state write | `TransactionContract.sol:submitTransaction()` |
| Reentrancy attack | Recursive call before balance update | CEI pattern (Checks-Effects-Interactions) | Balance deducted first, event emitted last |
| Address injection | Malformed address bypasses validation | Pre-compiled regex gate | `validate_address()` |
| Dependency CVE | Vulnerable transitive dependency | pip-audit on every CI run | `ci.yml:dependency-check` |
| Code vulnerability | SQL injection, path traversal, etc. | Bandit static analysis | `ci.yml:security` |
| Passphrase exposure | Log or stack trace leaks | Function (not global), never logged | `config.get_encryption_passphrase()` |

### Why Separate `requirements.txt` and `requirements-dev.txt`

The `ci.yml` runs `pip-audit -r requirements.txt` — auditing **only** production dependencies. If dev tools (Bandit, Ruff, pytest) were in `requirements.txt`, their transitive dependencies (e.g., `pygments`, pulled in by Bandit) would be included in the audit. `pygments` had CVE-2026-4539 at the time of development; including it in the production audit would create a false positive that would block CI. The split explicitly documents which dependencies are runtime security concerns.

---

## Performance & Optimization

### PoW Mining Performance

At difficulty 3 (the default), mining requires on average 16³ = 4,096 SHA-256 computations. Python's `hashlib.sha256` is a thin wrapper around OpenSSL's C implementation, making each hash approximately 1–5 microseconds on modern hardware. Expected mining time: **4–20ms at difficulty 3**.

At difficulty 4: 65,536 iterations → 65ms–325ms. At difficulty 5: ~1M iterations → 1–5 seconds.

**No GPU acceleration**: SHA-256 PoW is implemented in pure Python/hashlib. Production miners (ASIC, GPU) are orders of magnitude faster. This is appropriate for an educational simulation.

### Regex Pre-Compilation

```python
_ETH_ADDRESS_PATTERN: re.Pattern[str] = re.compile(r"^0x[0-9a-fA-F]{40}$")
```
The pattern is compiled at module import time, not at each `validate_address()` call. For a dataset with 10,000 address candidates, this saves 10,000 compilation operations.

### Mempool Data Structure

`collections.deque` provides O(1) `append` (right) and O(1) `popleft`. A `list` would provide O(1) `append` but O(n) `pop(0)`. For mempools with hundreds of transactions, this difference is significant.

### Canonical JSON Caching

Block hashes are computed in `__post_init__` and stored. During chain validation (`is_valid_chain()`), `block.compute_hash()` is called again for each block — there is no caching of the recomputed hash. This is a deliberate design choice: caching would prevent the tamper detection demo from working correctly (a cached "recomputed" hash would return the pre-mutation value).

### Frontend Polling vs WebSocket

The 3-second polling interval was chosen as a balance between responsiveness and server load. WebSocket integration would enable push-based updates with sub-second latency, but would add complexity (Flask-SocketIO dependency, keepalive management, reconnection logic) without educational benefit.

---

## Error Handling & Logging

### Logging Architecture

Every module acquires its logger via `wallet.config.configure_logging(__name__)`:

```python
logger = configure_logging(__name__)
```

The logger name is the Python module path (e.g., `wallet.address_loader`, `chain.consensus`). This enables fine-grained log filtering in production — `LOG_LEVEL=WARNING` suppresses info-level mining progress logs while preserving warnings and errors.

**Log format**: `2026-04-29 12:34:56 | chain.consensus | INFO | Mining block #3 with difficulty 3`

**What is NOT logged** (by design):
- Private key values (never held as strings after loading)
- Encryption passphrase (read directly from `os.getenv()`, returned immediately)
- Full address lists at DEBUG level (prevents wallet identity leakage in aggregated logs)

### API Error Handling

All Flask routes use `try/except` to convert domain exceptions to structured JSON:

```python
try:
    tx_id = node.blockchain.mempool.add_transaction(tx)
except OverflowError as exc:
    return jsonify({"error": str(exc)}), 503
```

No raw exception messages are returned without sanitization. The `OverflowError` message from `mempool.py` is a safe, pre-written string with no stack trace information.

### CI Failure Modes

| CI Job | Failure Condition | Impact |
|---|---|---|
| Ruff lint | Any style violation or unused import | Blocks `test` job |
| Bandit | Medium or high severity finding | Blocks `test` job |
| pip-audit | Any CVE in `requirements.txt` | Blocks `test` job |
| Hardhat compile | Solidity syntax or type error | Does not block `test` job (parallel) |
| pytest | Any test failure OR coverage < 80% | Marks commit as failed |

---

## Research & Engineering Contributions

### 1. BIP-62 Low-S Normalization in Pure Python
While this standard is well-documented for Bitcoin, clean Python implementations using the modern `cryptography` library (rather than the deprecated `ecdsa` library) are rare in educational contexts. This implementation provides a clear, annotated reference for secp256k1 malleability defense.

### 2. Canonical JSON Serialization as a Security Control
The use of `json.dumps(sort_keys=True, separators=(",", ":"))` as a cryptographic canonicalization method is documented in the IETF RFC 8785 (JCS — JSON Canonicalization Scheme). This project demonstrates why canonicalization is a security requirement (not just style) in systems where data structure hashing drives integrity proofs.

### 3. Layered Security Defense-in-Depth
The system implements defense-in-depth at three independent levels:
- **Cryptographic layer**: ECDSA signature verification
- **Protocol layer**: Nonce-based replay protection
- **Smart contract layer**: Atomic balance deduction preventing double-spend
Any single layer failing does not compromise the others.

### 4. Application Factory + Singleton Pattern for Testable Blockchain APIs
The combination of `create_app()` (Flask factory) and `get_node()` / `reset_node()` (lazy singleton with explicit reset) solves a fundamental problem in blockchain API testing: each test needs an isolated chain state without restarting the Flask server. This pattern could be generalized to any stateful Flask application.

### 5. Separation of Dev and Production Dependencies in CI
Explicitly separating `requirements.txt` (production) from `requirements-dev.txt` (tooling) and running `pip-audit` only against production dependencies eliminates false positives from dev tool transitive dependencies — a practical CI engineering contribution.

---

## Limitations

1. **In-memory only**: The blockchain resets on Flask restart. There is no persistence layer (database, file system serialization) for the chain or mempool.

2. **Simulated P2P**: Node peers are Python objects in the same process. There is no TCP/IP networking, no peer discovery, no NAT traversal. Real P2P would require a networking layer (asyncio, libp2p, or similar).

3. **Single-threaded mining**: `mine_block()` blocks the Flask request thread during PoW. At difficulty 5+, this could cause HTTP timeouts. Production implementations use background threads, worker processes, or dedicated mining daemons.

4. **No nonce tracking in API**: While the signing module supports replay protection via nonces, the Flask API does not currently persist used nonces. A submitted transaction could theoretically be re-submitted with the same nonce+signature. The `SECURITY.md` explicitly notes this as a Phase 6 TODO.

5. **Smart contract not integrated with Python chain**: The Python blockchain and the Solidity contract are two independent systems. They are not synchronized — a transaction approved on the smart contract does not automatically appear in the Python blockchain and vice versa.

6. **No peer authentication**: The `sync_chain()` function accepts chain data from any object claiming to be a peer. In a real network, peer identities must be authenticated (e.g., via TLS certificates or Ethereum-style node IDs).

7. **No fee prioritization in mempool**: Transactions are selected FIFO. Production mempools prioritize by fee (miners earn more from high-fee transactions) or by fee-per-byte.

---

## Future Improvements

| Priority | Enhancement | Technical Approach |
|---|---|---|
| High | Persistent chain storage | SQLite via SQLAlchemy; serialize Block objects; load on startup |
| High | Mempool nonce tracking | Redis set for used nonces; TTL-based expiry |
| High | Async mining | `asyncio` background task or Celery worker; SSE for real-time mining updates |
| Medium | Real P2P networking | `libp2p` or custom asyncio TCP; peer discovery via mDNS or a bootstrap node |
| Medium | Transaction fee prioritization | Max-heap mempool sorted by fee-per-byte |
| Medium | Merkle proof generation | `get_proof(tx_hash)` returns sibling hashes for O(log n) inclusion proof |
| Medium | EIP-55 checksum address validation | Enforce checksum-validated addresses instead of case-insensitive hex |
| Low | WebSocket chain updates | Flask-SocketIO; push block events on mining instead of 3-second polling |
| Low | Multi-node dashboard | UI showing multiple Node instances and their sync state |
| Low | UTXO model | Replace account-based balances with Bitcoin-style unspent transaction output tracking |
| Low | Signature aggregation | BLS12-381 aggregate signatures for reduced block size |

---

## Installation Guide

### Prerequisites

| Requirement | Version | Check Command |
|---|---|---|
| Python | ≥ 3.13 | `python --version` |
| pip or uv | Latest | `pip --version` / `uv --version` |
| Node.js | 22 | `node --version` |
| npm | Latest | `npm --version` |
| Ganache | GUI or CLI | (optional, for smart contract) |

### Step 1 — Clone Repository
```bash
git clone https://github.com/Dharaneswara-Reddy/secure-blockchain-financial-txn-system.git
cd secure-blockchain-financial-txn-system
```

### Step 2 — Configure Environment
```bash
# The .env file is already present in the repository
# Verify it contains:
cat .env
# WALLET_ENCRYPTION_PASSPHRASE=Blockchain@SecureKey#2024!
# DATASET_PATH=datasets/Eth_Txs.csv
# KEYSTORE_PATH=keystore
# LOG_LEVEL=INFO
```

### Step 3 — Install Python Dependencies
```bash
# Option A: pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Option B: uv (faster, recommended)
uv sync
uv add -r requirements-dev.txt
```

### Step 4 — Install Node.js Dependencies (for Smart Contract)
```bash
npm install
npx hardhat compile   # validates TransactionContract.sol
```

### Step 5 — Verify web3 Connectivity (optional)
```bash
# Start Ganache first, then:
python verify_setup.py
# Connected: True
# 0xAbC... → 100.0 ETH
```

---

## Usage Guide

### Run the Blockchain Node + REST API + Block Explorer
```bash
flask --app api/app.py run --debug
# → http://127.0.0.1:5000 (Block Explorer)
# → http://127.0.0.1:5000/api/chain/stats (API)
```

### Run the Full Test Suite
```bash
python -m pytest tests/ -v \
  --cov=wallet --cov=blockchain --cov=chain --cov=api \
  --cov-report=term-missing \
  --cov-report=html:htmlcov \
  --cov-fail-under=80
```

### Deploy Smart Contract
```bash
# Start Ganache on port 7545, then:
npx hardhat run scripts/deploy.js --network ganache
# → deployment.json written to project root
```

### Use the ContractInterface in Python
```python
from web3 import Web3
from blockchain.contract import ContractInterface

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
iface = ContractInterface.from_deployment_file(w3)

# Fund a wallet
iface.fund_wallet("0xAlice...", amount_ether=10.0, sender=w3.eth.accounts[0])

# Submit a transaction
tx_hash = iface.submit_transaction(
    sender="0xAlice...", receiver="0xBob...",
    value_ether=1.5, fee_ether=0.001
)

# Approve it (owner only)
iface.approve_transaction(tx_hash, sender=w3.eth.accounts[0])
```

### Use the Signer Module Directly
```python
from wallet.key_manager import generate_key_pair
from wallet.signer import create_nonce, sign_transaction, verify_signature

private_key, public_key = generate_key_pair()
tx = {"sender": "0xAlice", "receiver": "0xBob", "amount": 1.5}
nonce = create_nonce()

signature = sign_transaction(tx, private_key, nonce)
is_valid = verify_signature(signature, public_key, tx, nonce)
print(is_valid)  # True
```

---

## Conclusion

This project demonstrates that blockchain is not magic — it is a precise composition of well-understood cryptographic, data structure, and distributed systems primitives. Every security property of the system is traceable to a specific algorithmic decision: tamper evidence to SHA-256 hash chaining; transaction authenticity to ECDSA-SHA256 signatures; replay resistance to UUID4 nonces; malleability resistance to BIP-62 low-S normalization; consensus to Nakamoto's longest-chain rule; and double-spend prevention to atomic balance reservation.

The architecture is deliberately layered to allow each concern to be studied, tested, and extended independently. The cryptographic identity layer (`wallet/`) operates without knowledge of the blockchain. The blockchain engine (`chain/`) operates without knowledge of the API. The smart contract (`contracts/`) operates without knowledge of the Python simulation. This separation is both an engineering virtue and a pedagogical tool — it allows a reader to understand each component in isolation before studying how they compose into the full system.

For researchers and engineers using this as a reference: the most novel aspects of this implementation are the BIP-62 enforcement in the signer, the canonical JSON serialization as a cryptographic control, the application factory + singleton pattern enabling isolated blockchain API testing, and the separation of production and development dependencies to eliminate CI false positives. These patterns apply broadly beyond this specific domain.

---

## License

MIT License — see [LICENSE](LICENSE) for full text.

---

*Developed as a Semester 6 Blockchain Technology course project. All cryptographic primitives implemented from first principles for educational clarity. Not intended for production financial use.*
