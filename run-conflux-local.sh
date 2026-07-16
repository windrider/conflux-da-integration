#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Starting Conflux dev node (Solidity DA) on localhost..."

# Stop Docker conflux if running
cd "$ROOT"
docker compose stop conflux-chain 2>/dev/null || true

CONFLUX_DATA_DIR="$ROOT/blockchain/run"

if [ ! -d "$CONFLUX_DATA_DIR/blockchain_data" ]; then
    echo "Initializing Conflux data directory..."
    mkdir -p "$CONFLUX_DATA_DIR/blockchain_data"
fi

cat > "$CONFLUX_DATA_DIR/conflux.toml" << EOF
chain_id = 10
evm_chain_id = 10

mode = "dev"
dev_block_interval_ms = 1000
dev_allow_phase_change_without_peer = true
node_type = "archive"

target_block_gas_limit = 60000000

# No built-in da.rs — external DASigners.sol only
cipda = 999999999

jsonrpc_http_port = 12537
jsonrpc_ws_port = 12535
jsonrpc_http_eth_port = 8545
jsonrpc_ws_eth_port = 8546
jsonrpc_cors = "all"
jsonrpc_http_keep_alive = false

public_rpc_apis = "all"
public_evm_rpc_apis = "evm"

tcp_port = 32323

log_level = "info"
log_file = "$CONFLUX_DATA_DIR/conflux.log"

block_db_dir = "$CONFLUX_DATA_DIR/blockchain_data"
netconf_dir = "$CONFLUX_DATA_DIR/blockchain_data/net_config"

cip90_transition_height = 0
cip90_transition_number = 0
cip1559_transition_height = 999999999

hydra_transition_height = 999999999
hydra_transition_number = 999999999
dao_vote_transition_height = 999999999
dao_vote_transition_number = 999999999
cip43_init_end_number = 999999999
pos_reference_enable_height = 999999999

metrics_enabled = true
metrics_output_file = "$CONFLUX_DATA_DIR/metrics.log"
EOF

echo "Configuration: $CONFLUX_DATA_DIR/conflux.toml"

CONFLUX_BIN="$ROOT/blockchain/conflux-rust/target/release/conflux"
if [ ! -x "$CONFLUX_BIN" ]; then
    CONFLUX_BIN="$ROOT/blockchain/conflux"
fi

if [ ! -x "$CONFLUX_BIN" ]; then
    echo "Conflux binary not found. Run: ./blockchain/build-conflux.sh"
    exit 1
fi

exec "$CONFLUX_BIN" --config "$CONFLUX_DATA_DIR/conflux.toml"
