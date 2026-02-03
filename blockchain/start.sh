#!/bin/bash
set -e

echo "Starting Conflux node with DA support..."

# Initialize data directory if not exists
if [ ! -d "/data/blockchain_data" ]; then
    echo "Initializing Conflux data directory..."
    mkdir -p /data/blockchain_data
    echo "Data directory created"
fi

# Create genesis accounts file
mkdir -p ./run
cat > ./run/genesis_accounts.txt << 'EOF'
# Hardhat account #0
0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266=100000000000000000000000000
# Hardhat account #1
0x70997970C51812dc3A010C7d01b50e0d17dc79C8=100000000000000000000000000
# Hardhat account #2
0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC=100000000000000000000000000
# DA node signer account (from da-node logs)
0x9685c4eb29309820cdc62663cc6cc82f3d42e964=100000000000000000000000000
EOF

# Create Conflux configuration
cat > /data/conflux.toml << 'EOF'
# Network and chain configuration
chain_id = 10
evm_chain_id = 10

# Mode
mode = "dev"
dev_block_interval_ms = 1000
dev_allow_phase_change_without_peer = true
node_type = "archive"

# Genesis accounts
genesis_accounts = "./run/genesis_accounts.txt"

# Increase gas limit for DA contract deployment (60,000,000)
target_block_gas_limit = 60000000


# DA功能启用（从区块0开始）
cipda = 0

# RPC configuration
jsonrpc_http_port = 12537
jsonrpc_ws_port = 12535
jsonrpc_http_eth_port = 8545
jsonrpc_ws_eth_port = 8546
jsonrpc_cors = "all"
jsonrpc_http_keep_alive = false

# Public RPC APIs
public_rpc_apis = "all"
public_evm_rpc_apis = "evm"

# P2P
tcp_port = 32323

# Logging
log_level = "info"
log_file = "/data/conflux.log"

# Storage
block_db_dir = "/data/blockchain_data"
netconf_dir = "/data/blockchain_data/net_config"

# Disable single MPT storage for full node compatibility
# enable_single_mpt_storage = true

# Transaction type configuration
# Enable eSpace type 0 (EIP-155) transactions from block 0
cip90_transition_height = 0
cip90_transition_number = 0
# Disable EIP-1559 for demo (requires PoS)
cip1559_transition_height = 999999999

# Keep other CIP transitions disabled for demo
hydra_transition_height = 999999999
hydra_transition_number = 999999999
dao_vote_transition_height = 999999999
dao_vote_transition_number = 999999999
cip43_init_end_number = 999999999
# Disable PoS for dev mode (single node can't reach consensus)
pos_reference_enable_height = 999999999

# Metrics
metrics_enabled = true
metrics_output_file = "/data/metrics.log"
EOF

echo "Configuration created at /data/conflux.toml"
echo "Starting Conflux node..."

# Start Conflux - only use --config, no additional args needed
exec conflux --config /data/conflux.toml
