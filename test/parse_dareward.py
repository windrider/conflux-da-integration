import json
from pathlib import Path

from web3 import Web3

ROOT = Path(__file__).resolve().parents[1]
ADDRESSES_JSON = ROOT / "da-contract/0g-da-contract/deployments/zg/da-addresses.json"

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

with ADDRESSES_JSON.open() as f:
    da_entrance = json.load(f)["DAEntrance"]

event_sig = "DAReward(address,uint256,uint256,uint256,bytes32,uint256,uint256,uint256,uint256)"
topic0 = w3.keccak(text=event_sig).hex()

print(f"查询合约地址: {da_entrance}")

logs = w3.eth.get_logs(
    {
        "fromBlock": 0,
        "toBlock": "latest",
        "address": da_entrance,
        "topics": [topic0],
    }
)

print(f"找到 {len(logs)} 个 DAReward 事件\n")

for i, log in enumerate(logs[:5]):
    print(f"=== 事件 {i+1} ===")
    print(f'区块号: {log["blockNumber"]}')
    print(f'交易哈希: {log["transactionHash"].hex()}')

    beneficiary = "0x" + log["topics"][1].hex()[-40:]
    sample_round = int(log["topics"][2].hex(), 16)
    epoch = int(log["topics"][3].hex(), 16)

    print(f"Beneficiary (受益人): {beneficiary}")
    print(f"Sample Round (采样轮次): {sample_round}")
    print(f"Epoch (时期): {epoch}")

    data_bytes = log["data"]
    quorum_id = int.from_bytes(data_bytes[0:32], "big")
    data_root = "0x" + data_bytes[32:64].hex()
    quality = int.from_bytes(data_bytes[64:96], "big")
    line_index = int.from_bytes(data_bytes[96:128], "big")
    subline_index = int.from_bytes(data_bytes[128:160], "big")
    reward_wei = int.from_bytes(data_bytes[160:192], "big")
    reward_cfx = w3.from_wei(reward_wei, "ether")

    print(f"Quorum ID: {quorum_id}")
    print(f"Data Root: {data_root}")
    print(f"Quality: {quality}")
    print(f"Line Index: {line_index}")
    print(f"Subline Index: {subline_index}")
    print(f"Reward: {reward_cfx} CFX ({reward_wei} wei)")
    print()

print("\n=== 统计信息 ===")
beneficiaries = set()
total_reward = 0

for log in logs:
    beneficiary = "0x" + log["topics"][1].hex()[-40:]
    beneficiaries.add(beneficiary)
    reward_wei = int.from_bytes(log["data"][160:192], "big")
    total_reward += reward_wei

print(f"总事件数: {len(logs)}")
print(f"不同受益人: {len(beneficiaries)}")
for addr in beneficiaries:
    print(f"  - {addr}")
print(f"\n总奖励: {w3.from_wei(total_reward, 'ether')} CFX")
if len(logs) > 0:
    print(f"平均奖励: {w3.from_wei(total_reward // len(logs), 'ether')} CFX")
