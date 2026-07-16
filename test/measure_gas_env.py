#!/usr/bin/env python3
"""
测量 gas 评估文档 §7.1 环境参数。在项目根目录执行：
  pip install web3
  python3 test/measure_gas_env.py
"""
from collections import Counter
from pathlib import Path

from web3 import Web3

RPC = "http://127.0.0.1:8545"
DA_ENTRANCE = "0x6Fefa456504C11B38444Cd66F9D3291270D58CB2"
DA_SIGNERS = "0x0888000000000000000000000000000000000003"

ROOT = Path(__file__).resolve().parents[1]
SIGNERS_ABI = ROOT / "da-node/0g-da-node/abis/IDASigners.json"


def main() -> None:
    w3 = Web3(Web3.HTTPProvider(RPC))
    if not w3.is_connected():
        print(f"无法连接 RPC: {RPC}")
        print("请先 docker compose up -d")
        return

    import json

    signers = w3.eth.contract(
        address=Web3.to_checksum_address(DA_SIGNERS),
        abi=json.loads(SIGNERS_ABI.read_text()),
    )

    block = w3.eth.get_block("latest")
    print("=== 7.1 测量环境（自动采集）===\n")
    print(f"Block gas limit: {block['gasLimit']}")
    print(f"Latest block:    {block['number']}\n")

    # epoch / quorum
    epoch = signers.functions.epochNumber().call()
    quorum_count = signers.functions.quorumCount(epoch).call()
    print(f"当前 epoch:           {epoch}")
    print(f"quorumCount(epoch):   {quorum_count}")

    quorum_len = 0
    if quorum_count > 0:
        quorum = signers.functions.getQuorum(epoch, 0).call()
        quorum_len = len(quorum)
        print(f"getQuorum(epoch,0) 长度: {quorum_len}  （即 quorum 行数/槽位数）")

    # NewSigner 注册数
    new_signer_topic = w3.keccak(text="NewSigner(address,(uint256,uint256),(uint256[2],uint256[2]))").hex()
    if not new_signer_topic.startswith("0x"):
        new_signer_topic = "0x" + new_signer_topic
    signer_logs = w3.eth.get_logs(
        {
            "fromBlock": 0,
            "toBlock": "latest",
            "address": Web3.to_checksum_address(DA_SIGNERS),
            "topics": [new_signer_topic],
        }
    )
    registered = len(signer_logs)
    print(f"\n已注册 DA Node（NewSigner 事件数）: {registered}")
    for i, log in enumerate(signer_logs):
        addr = "0x" + log["topics"][1].hex()[-40:]
        print(f"  [{i+1}] {addr}  block={log['blockNumber']}  tx={log['transactionHash'].hex()}")

    # ErasureCommitmentVerified → batch 大小（同一 tx 内事件条数）
    ev_topic = w3.keccak(text="ErasureCommitmentVerified(bytes32,uint256,uint256)").hex()
    if not ev_topic.startswith("0x"):
        ev_topic = "0x" + ev_topic
    ev_logs = w3.eth.get_logs(
        {
            "fromBlock": 0,
            "toBlock": "latest",
            "address": Web3.to_checksum_address(DA_ENTRANCE),
            "topics": [ev_topic],
        }
    )
    by_tx = Counter(log["transactionHash"].hex() for log in ev_logs)
    print(f"\nErasureCommitmentVerified 总事件数: {len(ev_logs)}")
    if by_tx:
        tx, cnt = by_tx.most_common(1)[0]
        print(f"典型 submitVerifiedCommitRoots batch（单 tx 最多事件数）: {cnt}")
        print(f"  示例 txHash: {tx}")
        receipt = w3.eth.get_transaction_receipt(tx)
        print(f"  该 tx gasUsed: {receipt['gasUsed']}")
    else:
        print("尚无 ErasureCommitmentVerified 事件，请先跑完一次数据上传+确认流程")

    # bitmap hit：从该 tx 的 getAggPkG1 eth_call（需解码 calldata，简化：提示查链日志）
    print("\nbitmap 命中 signer 数（hit/total）:")
    print("  方法1: docker compose logs conflux-chain 2>&1 | grep GET_AGG_PK_G1 | tail -5")
    print("  方法2: 见文档 §7.1.1 从 submitVerifiedCommitRoots 交易解码后 eth_call getAggPkG1")

    print("\ncompose 启动时间:")
    print("  docker inspect $(docker compose ps -q conflux-chain) --format '{{.State.StartedAt}}'")


if __name__ == "__main__":
    main()
