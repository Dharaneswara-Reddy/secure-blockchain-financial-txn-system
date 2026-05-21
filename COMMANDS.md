# All Commands — Quick Reference

---

## 1. FIRST-TIME SETUP (run once)

```bash
# Navigate to project
cd ~/Documents/Sem-6/Block_Chain_Project

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install Node.js dependencies (for Hardhat + Solidity)
npm install

# Create .env file (if not exists)
echo 'WALLET_ENCRYPTION_PASSPHRASE="your-secure-passphrase-here"' > .env
```

---

## 2. START THE BLOCK EXPLORER (Main Demo)

```bash
# Activate venv first
source venv/bin/activate

# Run Flask server
flask --app api/app.py run --debug

# Open in browser: http://127.0.0.1:5000
```

**What you can do on the dashboard:**
- Submit transactions
- Mine blocks (click Mine)
- See chain stats (height, difficulty, validity)
- Tamper with a block → badge turns red
- Restore chain → badge turns green

---

## 3. SMART CONTRACT ON ETHEREUM (Ganache Demo)

```bash
# Step 1: Open Ganache GUI application (must be running on port 7545)

# Step 2: Compile the Solidity contract
npx hardhat compile

# Step 3: Deploy to Ganache
npx hardhat run scripts/deploy.js --network ganache

# Step 4: Run the Ethereum demo script
source venv/bin/activate
python demo_ethereum.py

# Then show Ganache GUI → Transactions tab to faculty
```

---

## 4. API ENDPOINTS (Manual Testing with curl)

```bash
# Make sure Flask is running first (see section 2)

# Submit a transaction
curl -X POST http://127.0.0.1:5000/api/transactions/submit \
  -H "Content-Type: application/json" \
  -d '{"sender":"0x1234abcd","receiver":"0x5678efgh","amount":5.0}'

# View pending transactions
curl http://127.0.0.1:5000/api/transactions/pending

# Mine a block
curl -X POST http://127.0.0.1:5000/api/mine

# View full blockchain
curl http://127.0.0.1:5000/api/blocks

# View single block
curl http://127.0.0.1:5000/api/blocks/1

# Chain stats
curl http://127.0.0.1:5000/api/chain/stats

# Validate chain
curl http://127.0.0.1:5000/api/chain/validate

# Tamper with block 1 (inject fake transaction)
curl -X POST http://127.0.0.1:5000/api/tamper/1

# Restore chain
curl -X POST http://127.0.0.1:5000/api/chain/restore
```

---

## 5. RUN ALL TESTS

```bash
source venv/bin/activate

# Run all tests with coverage
pytest --cov=. --cov-report=term-missing

# Run tests for a specific module
pytest tests/test_block.py -v
pytest tests/test_mempool.py -v
pytest tests/test_blockchain.py -v
pytest tests/test_consensus.py -v
pytest tests/test_signer.py -v
pytest tests/test_merkle.py -v

# Run a single test function
pytest tests/test_signer.py::test_sign_and_verify -v
```

---

## 6. SECURITY SCANNING

```bash
source venv/bin/activate

# Lint check (Ruff)
ruff check .

# Security scan (Bandit)
bandit -r . -x ./venv,./node_modules,./tests -ll

# CVE dependency audit
pip-audit -r requirements.txt
```

---

## 7. VERIFY GANACHE CONNECTION

```bash
source venv/bin/activate
python verify_setup.py
```

---

## 8. COMPILE SOLIDITY CONTRACT ONLY

```bash
npx hardhat compile
# Output: artifacts/contracts/TransactionContract.sol/TransactionContract.json
```

---

## 9. GENERATE DIAGRAMS (Graphviz)

```bash
# High-level workflow diagram
dot -Tpng diagram_highlevel.dot -o diagram_highlevel.png

# PPT architecture diagram
dot -Tpng diagram_ppt.dot -o diagram_ppt.png -Gdpi=150

# Architecture diagram
dot -Tpng diagram_architecture.dot -o diagram_architecture.png

# Transaction flow diagram
dot -Tpng diagram_transaction_flow.dot -o diagram_transaction_flow.png

# Consensus diagram
dot -Tpng diagram_consensus.dot -o diagram_consensus.png
```

---

## 10. COMPILE LATEX REPORT

```bash
# Compile (run twice for TOC)
pdflatex project_report.tex
pdflatex project_report.tex

# Output: project_report.pdf
```

---

## 11. INTERACTIVE NOTEBOOK

```bash
source venv/bin/activate
jupyter notebook experiment.ipynb
```

---

## 12. COMMON ISSUES & FIXES

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` | Run `source venv/bin/activate` first |
| Flask won't start | Check if port 5000 is free: `lsof -i :5000` |
| Ganache connection refused | Open Ganache GUI, check it's on port 7545 |
| `deployment.json` not found | Run `npx hardhat run scripts/deploy.js --network ganache` |
| Hardhat compile fails | Run `npm install` first |
| Permission denied on .env | Run `chmod 600 .env` |
| Tests fail with passphrase error | Make sure `.env` has `WALLET_ENCRYPTION_PASSPHRASE` set |
