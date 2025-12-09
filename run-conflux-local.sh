#!/bin/bash
set -e

echo "Starting Conflux node with DA support on localhost..."

# 停止 Docker 中的 conflux
cd /home/songbozhi/0g-da-integration/conflux-da-integration
docker-compose stop conflux-chain 2>/dev/null || true

# 设置环境变量
export CONFLUX_DATA_DIR=/home/songbozhi/0g-da-integration/conflux-da-integration/blockchain/run

# Initialize data directory if not exists
if [ ! -d "$CONFLUX_DATA_DIR/blockchain_data" ]; then
    echo "Initializing Conflux data directory..."
    mkdir -p $CONFLUX_DATA_DIR/blockchain_data
    echo "Data directory created"
fi

# 创建配置文件
cat > $CONFLUX_DATA_DIR/conflux.toml << 'EOF'
# Network and chain configuration
chain_id = 10
evm_chain_id = 10

# Mode
mode = "dev"
dev_block_interval_ms = 1000
dev_allow_phase_change_without_peer = true
node_type = "archive"

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
log_file = "$CONFLUX_DATA_DIR/conflux.log"

# Storage
block_db_dir = "$CONFLUX_DATA_DIR/blockchain_data"
netconf_dir = "$CONFLUX_DATA_DIR/blockchain_data/net_config"

# Transaction type configuration
# Enable eSpace type 0 (EIP-155) transactions from block 0
cip90_transition_height = 0
cip90_transition_number = 0
# Disable EIP-1559 for demo (requires PoS, we use Type 0 transactions)
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
metrics_output_file = "$CONFLUX_DATA_DIR/metrics.log"
EOF

echo "Configuration created at $CONFLUX_DATA_DIR/conflux.toml"
echo "Starting Conflux node..."

# 启动 Conflux
cd /home/songbozhi/0g-da-integration/conflux-da-integration/blockchain/conflux-rust
exec ./target/release/conflux --config $CONFLUX_DATA_DIR/conflux.toml
