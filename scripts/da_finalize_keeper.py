#!/usr/bin/env python3
"""
Official DA finalize keeper (dev / testnet).

DASigners.finalizeEpoch() is permissionless — anyone may call it. This service is the
operational trigger run by the chain/DA maintainer; community can run their own copy.

Env:
  RPC_URL              default http://127.0.0.1:8545
  KEEPER_PRIVATE_KEY   hex without 0x (dev: same as contract deployer)
  DASIGNERS_ADDRESS    or read from DEPLOYMENTS_JSON
  EPOCH_BLOCKS         default 100
  POLL_INTERVAL_SEC    default 10
  MIN_BLOCK_GAS        default 160000000 (wait until eSpace block gasLimit reaches this)
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from web3 import Web3
from web3.exceptions import ContractLogicError

DEFAULT_DEPLOYMENTS = Path(
    os.environ.get(
        "DEPLOYMENTS_JSON",
        "/deployments/zg/da-addresses.json",
    )
)
SIGNERS_ABI = Path(
    os.environ.get(
        "SIGNERS_ABI",
        "/abis/IDASigners.json",
    )
)


def load_signers_address(w3: Web3) -> str:
    if addr := os.environ.get("DASIGNERS_ADDRESS"):
        return w3.to_checksum_address(addr)
    path = Path(os.environ.get("DEPLOYMENTS_JSON", DEFAULT_DEPLOYMENTS))
    if not path.is_file():
        raise FileNotFoundError(f"Set DASIGNERS_ADDRESS or deploy to {path}")
    data = json.loads(path.read_text())
    return w3.to_checksum_address(data["DASigners"])


def main() -> int:
    rpc = os.environ.get("RPC_URL", "http://127.0.0.1:8545")
    key_hex = os.environ.get(
        "KEEPER_PRIVATE_KEY",
        "02c3357d2ae0a59e18f62ab69093cc22eac1a25c9f78af7f78650939ecda5f62",
    )
    epoch_blocks = int(os.environ.get("EPOCH_BLOCKS", "100"))
    poll = float(os.environ.get("POLL_INTERVAL_SEC", "10"))
    min_block_gas = int(os.environ.get("MIN_BLOCK_GAS", "200000000"))

    w3 = Web3(Web3.HTTPProvider(rpc))
    if not w3.is_connected():
        print(f"Cannot connect to {rpc}", file=sys.stderr)
        return 1

    account = w3.eth.account.from_key(key_hex)
    signers_addr = load_signers_address(w3)
    abi = json.loads(SIGNERS_ABI.read_text())
    signers = w3.eth.contract(address=signers_addr, abi=abi)

    print("DA finalize keeper", flush=True)
    print(f"  rpc:      {rpc}", flush=True)
    print(f"  keeper:   {account.address}", flush=True)
    print(f"  signers:  {signers_addr}", flush=True)
    print(
        f"  epochBlocks={epoch_blocks} poll={poll}s minBlockGas={min_block_gas}",
        flush=True,
    )

    while True:
        try:
            block = w3.eth.block_number
            clock_epoch = block // epoch_blocks
            finalized = signers.functions.lastFinalizedEpoch().call()
            block_gas_limit = int(w3.eth.get_block("latest")["gasLimit"])

            if finalized >= clock_epoch:
                print(
                    f"block={block} clock_epoch={clock_epoch} finalized={finalized} ok",
                    flush=True,
                )
            elif block_gas_limit < min_block_gas:
                print(
                    f"block={block} waiting for eSpace gasLimit >= {min_block_gas} "
                    f"(current {block_gas_limit})",
                    flush=True,
                )
            else:
                next_epoch = finalized + 1
                tx_gas_cap = block_gas_limit - 100_000
                try:
                    tx_gas = signers.functions.finalizeEpoch().estimate_gas(
                        {"from": account.address}
                    )
                    tx_gas = min(int(tx_gas * 11 // 10), tx_gas_cap)
                except Exception as e:
                    print(
                        f"block={block} gasLimit={block_gas_limit} "
                        f"estimate finalize epoch {next_epoch} failed: {e}",
                        flush=True,
                    )
                    time.sleep(poll)
                    continue

                print(
                    f"block={block} clock_epoch={clock_epoch} finalized={finalized} "
                    f"→ finalize epoch {next_epoch} gas={tx_gas}",
                    flush=True,
                )
                nonce = w3.eth.get_transaction_count(account.address)
                tx = signers.functions.finalizeEpoch().build_transaction(
                    {
                        "from": account.address,
                        "nonce": nonce,
                        "gas": tx_gas,
                        "gasPrice": w3.eth.gas_price,
                        "chainId": w3.eth.chain_id,
                    }
                )
                signed = account.sign_transaction(tx)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                status = receipt.get("status", 0)
                gas_used = receipt.get("gasUsed", 0)
                if status != 1:
                    print(
                        f"  finalize reverted tx={tx_hash.hex()} gasUsed={gas_used}",
                        file=sys.stderr,
                        flush=True,
                    )
                else:
                    print(
                        f"  finalized epoch {next_epoch} tx={tx_hash.hex()} gasUsed={gas_used}",
                        flush=True,
                    )
        except ContractLogicError as e:
            print(f"contract error: {e}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"keeper error: {e}", file=sys.stderr, flush=True)

        time.sleep(poll)


if __name__ == "__main__":
    raise SystemExit(main())
