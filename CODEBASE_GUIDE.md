# 🗺️ Codebase Deep-Dive Guide

A file-by-file walkthrough of everything in this project — what each file does, why it exists, and what is happening inside it line by line at a conceptual level.

---

## Module Map

```
Block_Chain_Project/
├── wallet/          ← Cryptographic identity (keys, signing, addresses)
├── chain/           ← Raw blockchain engine (blocks, PoW, mempool, P2P)
├── blockchain/      ← Python wrapper around the Solidity smart contract
├── api/             ← Flask REST API + Block Explorer frontend
├── contracts/       ← Solidity smart contract source
├── scripts/         ← Hardhat deployment script
├── tests/           ← 13 pytest test modules
└── .github/         ← GitHub Actions CI pipeline
```

---

## 📁 `wallet/` — Cryptographic Identity Layer

This entire package exists to answer: **"Who is this user, and can we trust their signature?"**

---

### `wallet/config.py`

**Role:** Single source of truth for all configuration. Everything reads from here — never from raw `os.getenv` sprinkled through the codebase.

**What happens inside:**
1. At import time, `load_dotenv()` reads the `.env` file from the project root into `os.environ`
2. `DATASET_PATH` and `KEYSTORE_PATH` are resolved as `pathlib.Path` objects (absolute, relative to project root)
3. `get_encryption_passphrase()` is a **function**, not a module-level variable — this is intentional. If it were a global, any `vars(module)` call or stack trace could leak the passphrase. Reading it fresh each call and never caching it prevents this
4. `configure_logging(name)` returns a `logging.Logger` configured with a timestamp formatter. The guard `if not logger.handlers` prevents duplicate handlers when the same logger is requested multiple times (common in testing)

**Key design decision:** `get_encryption_passphrase()` raises `KeyError` immediately if the env var is unset — **fail-fast** prevents silent operation with an empty passphrase that would create unencrypted keys.

---

### `wallet/exceptions.py`

**Role:** Domain-specific exception hierarchy. Lets callers write precise `except` blocks instead of catching broad `Exception`.

**What happens inside:**
- `WalletBaseError(Exception)` — base class, catches all wallet errors in one `except` if needed
- `InvalidAddressError` — address regex failed or wrong type
- `DatasetLoadError` — CSV not found, missing columns, or empty
- `KeyGenerationError` — cryptography library failed to generate a key pair
- `KeyStorageError` — covers both save (permission error, disk full) and load (wrong passphrase, file not found, corrupted)
- `SignatureError` — signing failed (bad key, non-serialisable data)
- `VerificationError` — signature structurally invalid (wrong length) OR high-S malleability detected

---

### `wallet/address_loader.py`

**Role:** Parse a real Ethereum transaction CSV dataset and extract unique, validated wallet addresses.

**What happens inside step-by-step:**

1. **Compile regex once** — `_ETH_ADDRESS_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")` is compiled at module load time (not per-call) to avoid ReDoS risk from repeated compilation
2. **`validate_address(address)`** — Runs the regex match. Raises `InvalidAddressError` if the input is not even a string (prevents `None`, `int` etc. from silently failing)
3. **`load_addresses(csv_path)`** — Opens the CSV with `pandas.read_csv`, reading **only** `From` and `To` columns (reduces memory usage). Unions both columns into a single candidate set. Iterates over candidates, calling `validate_address`. Non-hex labels like `"BinanceWallet"` fail the regex and are logged as warnings. Valid addresses are **lowercased** before storing (Ethereum addresses are case-insensitive; lowercase is the canonical form for storage and comparison)
4. Returns a `set[str]` of validated, lowercased addresses

**Why a set?** Sets deduplicate automatically. One address appearing in 1000 transactions still produces only one key pair.

---

### `wallet/key_manager.py`

**Role:** Generate ECDSA key pairs on secp256k1, encrypt and persist them to disk, load them back.

**What happens inside step-by-step:**

**`generate_key_pair()`**
- Calls `ec.generate_private_key(ec.SECP256K1())` — the `cryptography` library uses the OS CSPRNG (`os.urandom` on Linux via `/dev/urandom`)
- Derives the public key with `private_key.public_key()`
- Returns `(private_key, public_key)` — both are in-memory objects only

**`serialize_private_key(private_key, passphrase)`**
- Calls `private_key.private_bytes(...)` with:
  - `Encoding.PEM` — ASCII-armored base64 format
  - `PrivateFormat.PKCS8` — standard container format
  - `BestAvailableEncryption(passphrase.encode("utf-8"))` — selects AES-256-CBC + PBKDF2-HMAC; the library picks the strongest available algorithm
- Returns encrypted PEM bytes

**`save_keys(address, private_key, public_key, passphrase)`**
- Converts address to filename: strips `0x`, lowercases → e.g. `abc123..._private.pem`
- Creates the keystore directory if it doesn't exist
- Writes the encrypted private key PEM, then calls `os.chmod(path, 0o600)` — POSIX owner-read-only permissions
- Writes the unencrypted public key PEM (public keys are not secret)

**`load_private_key(address, passphrase)`**
- Constructs the file path from address
- Reads the PEM bytes, calls `serialization.load_pem_private_key(data, password=passphrase.encode("utf-8"))` — decryption happens here; wrong passphrase raises `ValueError` which is caught and re-raised as `KeyStorageError`
- Type-checks the result is actually an `EllipticCurvePrivateKey` (not an RSA or DSA key)

**`generate_keys_for_addresses(addresses)`**
- Iterates over the address set
- Checks if `<address>_private.pem` already exists — skips if so (**idempotent**)
- Generates and saves key pair for new addresses
- Returns count of newly generated pairs

---

### `wallet/signer.py`

**Role:** Sign transaction data with a private key; verify a signature with a public key. Implements replay protection and malleability protection.

**Constants:**
- `_SECP256K1_ORDER` — the curve group order N (a large prime, ~2^256). All ECDSA arithmetic is mod N
- `_SECP256K1_HALF_ORDER` — N//2, used for the low-S check
- `_SIGNATURE_SIZE = 64` — raw (r‖s), 32 bytes each

**`create_nonce()`** — Returns `str(uuid.uuid4())`. UUID4 uses `os.urandom()`, making it a CSPRNG-backed nonce.

**`_build_canonical_message(tx_data, nonce)`**
- Merges `{**tx_data, "__nonce__": nonce}` into one dict
- `json.dumps(..., sort_keys=True, separators=(",", ":"))` — sorted keys + no spaces = identical bytes regardless of Python dict insertion order or Python version
- Returns UTF-8 encoded bytes

**`_normalise_low_s(r, s)`**
- If `s > N/2`, sets `s = N - s`. Mathematical fact: `(r, s)` and `(r, N-s)` verify the same message, so we always pick the smaller s
- Follows Bitcoin BIP-62 convention, also used by Ethereum

**`sign_transaction(tx_data, private_key, nonce)`**
1. Builds canonical message bytes
2. Calls `private_key.sign(message, ec.ECDSA(hashes.SHA256()))` → DER-encoded signature
3. Decodes DER → `(r, s)` integers using `decode_dss_signature`
4. Normalises to low-S
5. Re-encodes as raw 64 bytes: `r.to_bytes(32, "big") + s.to_bytes(32, "big")`

**`verify_signature(signature, public_key, tx_data, nonce)`**
1. Decodes raw 64 bytes → `(r, s)` — raises `VerificationError` if length ≠ 64
2. Checks `s <= N/2` — raises `VerificationError` for high-S (malleability protection)
3. Rebuilds canonical message from `tx_data + nonce`
4. Re-encodes `(r, s)` to DER (library requires DER for `verify()`)
5. Calls `public_key.verify(...)` — raises `InvalidSignature` on failure, caught and returns `False`
6. Returns `True` on success

---

## 📁 `chain/` — Blockchain Engine

This package implements the blockchain from scratch — no libraries, just SHA-256 and logic.

---

### `chain/block.py`

**Role:** The atomic unit of the chain. A `Block` is an immutable record of a set of transactions.

**Fields:**
- `index` — position in chain (0 = genesis)
- `transactions` — list of transaction dicts
- `previous_hash` — SHA-256 hash of the previous block (the "link")
- `timestamp` — Unix float (seconds since epoch)
- `nonce` — integer adjusted during PoW mining
- `hash` — SHA-256 of all the above fields

**`__post_init__`** — Python dataclass hook called after `__init__`. If `hash` was not supplied (normal case), computes it immediately. This ensures every Block always has a valid hash from the moment it's constructed.

**`compute_hash()`**
- Builds a dict of all fields, serialises with `json.dumps(..., sort_keys=True, separators=(",",":"))`
- **Why sorted keys?** Python dicts preserve insertion order but we need the hash to be identical regardless of how the dict was constructed. Sorted keys = deterministic serialisation = deterministic hash.
- Returns hex-encoded SHA-256 digest

**`to_dict()`** — Returns a JSON-serialisable plain dict including a convenience `tx_count` field for the API.

**`GENESIS_PREV_HASH = "0" * 64`** — 64 zeros, the conventional "there is no previous block" sentinel value for the genesis block.

---

### `chain/merkle.py`

**Role:** Compute a Merkle root hash that cryptographically commits to an ordered list of transactions.

**How it works:**
1. Each transaction dict is deterministically serialised (`json.dumps` with sorted keys) and SHA-256 hashed → **leaf hashes**
2. If only one transaction, return its leaf hash directly
3. Otherwise, while more than one hash remains at the current level:
   - If the count is **odd**, duplicate the last hash (Merkle tree convention for odd-length levels)
   - Hash every adjacent pair together: `SHA256(hash[i] + hash[i+1])`
   - This halves the number of hashes each iteration
4. When only one hash remains, that is the **Merkle root**

**Why does this matter?** Any change to any transaction changes its leaf hash, which changes every parent hash up to the root, which changes the block hash, which breaks `previous_hash` of the next block — making silent modification detectable across the entire chain.

---

### `chain/mempool.py`

**Role:** An in-memory pool of unconfirmed transactions waiting to be mined into a block.

**Internal data structure:** `collections.deque` — O(1) appends and FIFO ordering. Not a `list` (which has O(n) `popleft`).

**`add_transaction(tx)`**
- Checks pool is not full (default max 1000 transactions)
- Stamps a UUID4 `id` and `submitted_at` Unix timestamp onto the transaction
- Appends to the deque
- Returns the generated UUID (so the caller can track the transaction)

**`select_transactions(max_count)`** — Returns the first `max_count` entries as a list. **Non-destructive** — does not remove from pool. Mining calls this, then calls `remove_transactions` after the block is confirmed.

**`remove_transactions(tx_ids)`** — Reconstructs the deque excluding the given IDs. Uses a `set` for O(1) ID lookups. Returns the count actually removed.

---

### `chain/blockchain.py`

**Role:** The ordered chain of blocks. Manages genesis creation, block addition with validation, and chain integrity checking.

**`__init__`** — Creates an empty chain and a `Mempool`, then immediately creates the genesis block.

**`_create_genesis_block(timestamp)`** — Creates `Block(index=0, transactions=[], previous_hash=GENESIS_PREV_HASH)`. The genesis block has no real predecessor, so `previous_hash` is 64 zeros by convention.

**`add_block(block)`**
- Validates `block.previous_hash == self.last_block().hash` — the new block must point at the current chain tip
- Validates `block.hash == block.compute_hash()` — the stored hash must match what the content actually hashes to (detects pre-tampered blocks)
- Returns `False` on either failure (does not raise, lets callers decide what to do)

**`is_valid_chain()`**
- Iterates from block 1 (skips genesis)
- For each block: checks stored hash == recomputed hash, and `previous_hash` == previous block's stored hash
- Returns `False` on first violation. This is what becomes `False` after a tamper attack.

---

### `chain/consensus.py`

**Role:** Proof-of-Work — makes block production computationally expensive, block verification cheap.

**`mine_block(block, difficulty)`**
- Sets `prefix = "0" * difficulty` (e.g. `"000"` for difficulty 3)
- Resets nonce to 0, computes initial hash
- Loop: increment nonce, recompute hash, check if it starts with `prefix`
- On success: block's `nonce` and `hash` are set and the block is returned
- For difficulty 3: expected ~4096 iterations on average (1/16^3 = 1/4096 probability per hash)

**`validate_proof(block, difficulty)`**
- Two checks: `block.hash.startswith(prefix)` AND `block.hash == block.compute_hash()`
- The second check prevents a miner from sending a fake hash that starts with zeros

**`adjust_difficulty(chain, current_difficulty)`**
- Only triggers every `DIFFICULTY_ADJUSTMENT_INTERVAL` (10) blocks
- Measures elapsed time for the last 10 blocks
- If `elapsed < expected/2` → blocks coming too fast → increase difficulty by 1
- If `elapsed > expected*2` → blocks coming too slow → decrease difficulty by 1 (min 1)
- Otherwise → unchanged
- Mirrors Bitcoin's adjustment algorithm but simplified (Bitcoin uses a 2-week window)

---

### `chain/node.py`

**Role:** Simulates a single participant in a blockchain P2P network. Ties together everything from `chain/`.

**`mine_pending_transactions(miner_address)`**
1. Calls `mempool.select_transactions()` (up to 10 by default)
2. Prepends a **coinbase transaction** — `{"sender": "NETWORK", "receiver": miner_address, "amount": 50.0, "type": "coinbase"}` — this is how miners get paid
3. Creates a new `Block` with the coinbase + pending transactions
4. Calls `mine_block(new_block, self.difficulty)` — the expensive PoW step
5. Calls `blockchain.add_block(mined)` — validates and appends
6. Removes mined transaction IDs from mempool
7. Calls `adjust_difficulty` to potentially change next block's target
8. **Broadcasts** the mined block to all registered peer nodes

**`_broadcast(block)`** — Calls `peer.receive_block(block, sender=self)` for each peer. Direct Python object method call (simulates network message passing).

**`receive_block(block, sender)`**
- Checks if the block extends our chain (`block.previous_hash == our_last_hash`)
- If yes: validates PoW with `validate_proof`, then `add_block`
- If no (chains diverged): checks if sender's chain is longer; if so, calls `sync_chain`

**`sync_chain(peer)`**
- Nakamoto consensus: if `len(peer.chain) > our_height` AND `peer.blockchain.is_valid_chain()` → replace our chain
- This ensures nodes always converge on the chain with the most accumulated PoW

---

## 📁 `blockchain/` — Smart Contract Python Interface

### `blockchain/contract.py`

**Role:** A clean, Pythonic wrapper around web3.py calls to the deployed Solidity `TransactionContract`.

**`load_abi(artifact_path)`** — Reads the Hardhat-compiled JSON artifact (`artifacts/contracts/TransactionContract.sol/TransactionContract.json`) and extracts the `"abi"` field. Using the compiled artifact (not a hardcoded ABI) ensures the Python interface always matches the deployed bytecode.

**`ContractInterface.__init__`**
- Stores the connected `Web3` instance
- Calls `Web3.to_checksum_address(address)` — converts address to EIP-55 checksum format, preventing mixed-case address bugs
- Creates `self.contract = w3.eth.contract(address=..., abi=...)` — the web3.py contract object

**`from_deployment_file(web3)`** — Reads `deployment.json` (written by `scripts/deploy.js`), extracts `address`, creates a `ContractInterface`. This factory method means Python code never needs to hardcode a contract address.

**`fund_wallet(wallet, amount_ether, sender)`**
- Converts ETH to wei: `w3.to_wei(amount_ether, "ether")`
- Calls `contract.functions.fundWallet(wallet).transact({"from": sender, "value": amount_wei})`
- Waits for the transaction receipt (blocks until mined)

**`submit_transaction(sender, receiver, value_ether, fee_ether)`**
- Transacts `submitTransaction(receiver, value_wei, fee_wei)` from `sender`
- After getting receipt, uses `contract.events.TransactionSubmitted().process_receipt(receipt)` to extract the `txHash` from the emitted event log
- Returns `bytes32` transaction hash

**`approve_transaction / reject_transaction`** — Simple `transact` calls gated by `onlyOwner` in Solidity. `reject_transaction` also accepts a `reason` string stored on-chain.

**Query methods** (`get_transaction`, `get_balance`, `get_tx_count`, `get_tx_hash_at`) — Use `.call()` instead of `.transact()`. `.call()` is a local simulation — no gas, no transaction, instant result.

**Event methods** (`get_submitted_events`, `get_approved_events`, `get_rejected_events`) — Use `contract.events.EventName.get_logs(fromBlock=0)` to retrieve historical events from the chain.

---

## 📁 `contracts/TransactionContract.sol`

**Role:** The on-chain source of truth for financial transactions. Immutable once deployed.

**State variables:**
- `address public owner` — set to `msg.sender` in constructor; only this address can approve/reject
- `mapping(address => uint256) public balances` — internal ledger; maps wallet address to wei balance
- `mapping(bytes32 => TxRecord) private _transactions` — transaction records keyed by unique hash
- `bytes32[] private _txHashes` — ordered list of all tx hashes (for iteration by index)

**`TxRecord` struct:** sender, receiver, value (wei), txFee (wei), Status enum (Pending/Approved/Rejected), timestamp, rejectReason string

**`fundWallet(address wallet) external payable`**
- `msg.value` is the ETH sent with the call
- Credits `balances[wallet] += msg.value`
- ETH stays locked in the contract until transactions are approved/rejected

**`submitTransaction(receiver, value, txFee) external returns (bytes32)`**
- Checks `receiver != address(0)` and `value > 0`
- Checks `balances[msg.sender] >= value + txFee` (sufficient balance)
- **Deducts funds first** (`balances[msg.sender] -= total`) before anything else — prevents reentrancy and double-spend
- Computes unique `txHash = keccak256(sender‖receiver‖value‖fee‖timestamp‖blockNumber‖txCount)` — context-dependent, impossible to predict before the transaction
- Stores `TxRecord` and appends hash to `_txHashes`
- Emits `TransactionSubmitted` event

**`approveTransaction(txHash) external onlyOwner`**
- Validates the record exists and is `Pending`
- Sets `status = Approved`
- Credits `balances[receiver] += value` (fee stays in contract, simulating miner reward)
- Emits `TransactionApproved`

**`rejectTransaction(txHash, reason) external onlyOwner`**
- Validates the record exists and is `Pending`
- Sets `status = Rejected`, stores `rejectReason`
- Full refund: `balances[sender] += value + txFee`
- Emits `TransactionRejected`

---

## 📁 `api/` — Flask REST API

### `api/state.py`

**Role:** Global Node singleton for the Flask process.

**Why a singleton?** The blockchain must persist across HTTP requests (unlike a database, it's in memory). A module-level `_node: Node | None = None` with a `get_node()` lazy initialiser ensures exactly one `Node` exists per process.

**`reset_node()`** sets `_node = None`. The next `get_node()` call creates a fresh node. Used in tests to get a clean slate between test functions.

---

### `api/app.py`

**Role:** Flask application factory.

**`create_app()`**
- Creates `Flask(__name__, static_folder="static")` — serves files from `api/static/` at the URL root
- Registers 4 blueprints with prefix `/api`
- Adds a root route `GET /` that serves `static/index.html` (the Block Explorer SPA)
- Returns the configured app

**Why a factory?** Testing requires creating fresh app instances. A factory function (`create_app()`) is the Flask-recommended pattern.

---

### `api/routes/blocks.py`

**`GET /api/blocks`** — Calls `get_node().blockchain.chain`, serialises each block with `to_dict()`, returns `{"blocks": [...], "count": N}`.

**`GET /api/blocks/<index>`** — Validates index is in `[0, height)`, returns one block dict or 404.

---

### `api/routes/transactions.py`

**`GET /api/transactions/pending`** — Returns `mempool.get_all()` snapshot.

**`POST /api/transactions/submit`** — Validates `sender`, `receiver`, `amount` fields present. Adds to mempool via `mempool.add_transaction(tx)`. Returns `{"tx_id": uuid, "status": "pending"}` with 201. Returns 503 if mempool is full (`OverflowError`).

---

### `api/routes/chain.py`

**`GET /api/chain/stats`** — Aggregates live stats from the Node object: height, total_transactions, difficulty, pending_transactions, last_hash, is_valid.

**`GET /api/chain/validate`** — Calls `blockchain.is_valid_chain()`, returns `{"valid": bool, "height": N}`.

**`POST /api/mine`** — Calls `node.mine_pending_transactions(miner_address)`, times it, returns the mined block dict with the time taken and new difficulty level. Returns 500 if mining fails.

---

### `api/routes/tamper.py`

**`POST /api/tamper/<index>`**
- The attack: `block.transactions.append({fake transaction})` **without calling** `block.hash = block.compute_hash()`
- Now `block.hash != block.compute_hash()` → `is_valid_chain()` returns `False`
- Response shows original hash, recomputed hash, and confirms `chain_valid: false`
- Educational purpose: demonstrates why blockchains are tamper-evident

**`POST /api/chain/restore`** — Calls `state_module.reset_node()`, then `get_node()` to lazily create a fresh clean node. Returns confirmation with height=1 (genesis only).

---

## 📁 `scripts/deploy.js`

**Role:** Hardhat deployment script for `TransactionContract`.

**What it does:**
1. Gets the first Hardhat signer (the deploying account)
2. Calls `ethers.getContractFactory("TransactionContract")` and `.deploy()`
3. Waits for deployment to be mined (`waitForDeployment()`)
4. Gets the contract address and deployment receipt
5. Writes `deployment.json` to the project root with: address, deployer, network, blockNumber, txHash, deployedAt timestamp
6. Python `ContractInterface.from_deployment_file(w3)` reads this file automatically

---

## 📁 `.github/workflows/ci.yml`

**Role:** 5-stage automated quality gate triggered on every push and PR to `main`.

| Job | Depends On | What Runs |
|---|---|---|
| `lint` | — | `ruff check` + `ruff format` on wallet/, tests/, blockchain/, chain/, api/ |
| `security` | — | `bandit -r wallet/ blockchain/ chain/ api/ -ll` — medium+high severity only |
| `dependency-check` | — | `pip-audit -r requirements.txt` — CVE scan of production deps only |
| `contracts-compile` | — | `npx hardhat compile` — validates Solidity syntax and types |
| `test` | lint, security, dependency-check | `pytest --cov --cov-fail-under=80` — full test suite with coverage |

The `test` job creates a `.env` file on the CI runner with a throwaway passphrase, ensuring `get_encryption_passphrase()` doesn't raise during tests.

---

## 📁 `tests/`

### `tests/conftest.py`

Shared fixtures available to all test files:
- `tmp_keystore` — temporary directory for key persistence tests (deleted after each test)
- `sample_addresses` — 3 hardcoded valid Ethereum-format addresses
- `sample_key_pair` — generates a fresh ECDSA key pair for each test
- `sample_tx_data` — a realistic transaction dict
- `sample_csv` — creates a temp CSV with 2 rows (one valid address, one `"BinanceWallet"` label)
- `test_passphrase` — a hardcoded passphrase string for encryption tests

### Test Coverage Summary

| File | Tests Cover |
|---|---|
| `test_address_loader.py` | Valid/invalid addresses, CSV loading, error conditions (missing file, bad columns, empty) |
| `test_key_manager.py` | Key gen, serialisation, save/load round-trip, wrong passphrase rejection, batch generation idempotency |
| `test_signer.py` | Sign/verify happy path, nonce mismatch, wrong key, malleability rejection, format errors |
| `test_block.py` | Hash computation, determinism (same inputs = same hash), `to_dict` output |
| `test_blockchain.py` | Add valid block, reject invalid `previous_hash`, reject tampered hash, `is_valid_chain` |
| `test_merkle.py` | Empty list, single tx, multiple txs, odd-count padding |
| `test_mempool.py` | Add, select, remove, overflow (`OverflowError`), `len` |
| `test_consensus.py` | PoW prefix check, `validate_proof`, `adjust_difficulty` up/down/unchanged |
| `test_node.py` | Mine with coinbase, broadcast to peer, sync chain, Nakamoto rule |
| `test_api.py` | Flask test client for all routes including error cases |
| `test_contract.py` | ContractInterface with mocked web3 — all CRUD operations, event parsing |

---

## 📁 Root-Level Files

| File | Purpose |
|---|---|
| `pyproject.toml` | Python project metadata, Ruff config (line length 120, LF endings), pytest config (`pythonpath = ["."]`), coverage source dirs |
| `requirements.txt` | **Production** runtime deps only: cryptography, flask, pandas, scikit-learn, web3, python-dotenv |
| `requirements-dev.txt` | **Dev/test** tools: bandit, pip-audit, pytest, pytest-cov, ruff |
| `hardhat.config.js` | Solidity 0.8.20 compiler with optimizer (200 runs), ganache (7545) and localhost (8545) network configs |
| `package.json` | Node.js deps: `hardhat`, `@nomicfoundation/hardhat-ethers`, `ethers` |
| `.env` | Local secrets — **not committed**. Must contain `WALLET_ENCRYPTION_PASSPHRASE` |
| `graph.html` | Interactive dependency graph (Vis.js) showing module relationships |
| `main.py` | Placeholder entry point (project scaffolding artifact) |
| `verify_setup.py` | Quick sanity check script to verify environment is configured |
| `experiment.ipynb` | Jupyter notebook for data exploration on the Ethereum CSV dataset |
| `datasets/Eth_Txs.csv` | Real Ethereum transaction data used for address extraction |
| `uv.lock` | Locked dependency tree (for `uv` package manager) |
