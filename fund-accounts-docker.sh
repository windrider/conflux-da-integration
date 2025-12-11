#!/bin/bash
set -e

echo "Funding DA accounts from Conflux genesis account (Docker version)..."

# Run funding script in a Python container with network access to conflux-chain
docker run --rm \
  --network container:conflux-da-integration-conflux-chain-1 \
  python:3.11-slim \
  bash -c '
    # Install web3.py
    pip install -q web3
    
    # Run Python funding script
    python3 << "PYEOF"
from web3 import Web3
import time

# Connect to Conflux (using localhost because we share network with conflux-chain)
w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))

# Wait for Conflux to be ready
print("Waiting for Conflux node to be ready...")
for i in range(30):
    try:
        if w3.is_connected():
            print("✓ Connected to Conflux node")
            break
    except:
        pass
    time.sleep(1)
else:
    print("Error: Cannot connect to Conflux node")
    exit(1)

# Genesis account
genesis_private_key = "0x46b9e861b63d3509c88b7817275a30d22d62c8cd8fa6486ddee35ef0d8e0495f"
account = w3.eth.account.from_key(genesis_private_key)
print(f"Using genesis account: {account.address}")

# Check genesis balance
genesis_balance = w3.eth.get_balance(account.address)
print(f"Genesis account balance: {w3.from_wei(genesis_balance, \"ether\")} CFX")

# Accounts to fund
accounts_to_fund = [
    ("0x9685c4eb29309820cdc62663cc6cc82f3d42e964", "DA node signer"),
    ("0x7Bbf300890857b8c241b219C6a489431669b3aFA", "DA node miner"),
    ("0xa223d305bc8147a75761f7f72f983e5eef867bd4", "DA contract deployer (old)"),
    ("0x5C33D16d3197AEDE38cD2FBc4E7Ff75edA97D81E", "DA contract deployer"),
    ("0xbDA94faf1CBb37Fc3ff66adcc70FF0e3036D19cD", "Disperser")
]

# Amount to send (100 CFX)
amount = w3.to_wei(100, "ether")

for to_address, name in accounts_to_fund:
    print(f"\nFunding {name}...")
    
    # Convert to checksum address
    to_address = w3.to_checksum_address(to_address)
    
    # Get nonce
    nonce = w3.eth.get_transaction_count(account.address)
    
    # Build transaction
    tx = {
        "nonce": nonce,
        "to": to_address,
        "value": amount,
        "gas": 21000,
        "gasPrice": w3.eth.gas_price,
        "chainId": w3.eth.chain_id
    }
    
    # Sign transaction
    signed_tx = w3.eth.account.sign_transaction(tx, genesis_private_key)
    
    # Send transaction
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Transaction sent: {tx_hash.hex()}")
    
    # Wait for confirmation
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"✓ Funded {name} with 100 CFX (block: {receipt[\"blockNumber\"]})")

print("\nVerifying balances...")
for to_address, name in accounts_to_fund:
    to_address = w3.to_checksum_address(to_address)
    balance = w3.eth.get_balance(to_address)
    print(f"{name}: {w3.from_wei(balance, \"ether\")} CFX")

print("\n✓ All accounts funded successfully!")
PYEOF
  '

echo ""
echo "✓ Funding complete!"
