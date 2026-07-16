from web3 import Web3
import time

w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))

print("Waiting for Conflux node...")
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

# 等待节点退出 catch up 模式
print("Waiting for node to finish syncing...")
for i in range(120):  # 最多等待 2 分钟
    try:
        # 尝试获取区块号，如果成功则节点已同步
        block = w3.eth.block_number
        if block > 0:
            print(f"✓ Node synced, current block: {block}")
            break
    except Exception as e:
        if "catch up mode" in str(e):
            if i % 10 == 0:
                print(f"  Still syncing... ({i}s)")
        else:
            pass
    time.sleep(1)
else:
    print("Warning: Node may still be syncing, proceeding anyway...")

genesis_private_key = "0x46b9e861b63d3509c88b7817275a30d22d62c8cd8fa6486ddee35ef0d8e0495f"
account = w3.eth.account.from_key(genesis_private_key)
print(f"Using genesis account: {account.address}")

genesis_balance = w3.eth.get_balance(account.address)
print(f"Genesis balance: {w3.from_wei(genesis_balance, 'ether')} CFX")
print()

accounts_to_fund = [
    ("0x9685c4eb29309820cdc62663cc6cc82f3d42e964", "DA node 1 signer"),
    ("0x7Bbf300890857b8c241b219C6a489431669b3aFA", "DA node 1 miner"),
    ("0xa223d305bc8147a75761f7f72f983e5eef867bd4", "DA contract deployer (old)"),
    ("0x5C33D16d3197AEDE38cD2FBc4E7Ff75edA97D81E", "DA contract deployer / finalize keeper (official ops)"),
    ("0xbDA94faf1CBb37Fc3ff66adcc70FF0e3036D19cD", "Disperser"),
    # DA node 2 accounts (Hardhat #3, #4, #5)
    ("0x90F79bf6EB2c4f870365E785982E1f101E93b906", "DA node 2 validator"),
    ("0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65", "DA node 2 signer"),
    ("0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc", "DA node 2 miner"),
    # DA node 3 accounts (Hardhat #6, #7, #8)
    ("0x976EA74026E726554dB657fA54763abd0C3a0aa9", "DA node 3 validator"),
    ("0x14dC79964da2C08b23698B3D3cc7Ca32193d9955", "DA node 3 signer"),
    ("0x23618e81E3f5cdF7f54C3d65f7FBc0aBf5B21E8f", "DA node 3 miner")
]

amount = w3.to_wei(100, "ether")

for to_address, name in accounts_to_fund:
    print(f"\nFunding {name}...")
    to_address = w3.to_checksum_address(to_address)
    
    # 重试机制，防止 catch up mode 错误
    for retry in range(10):
        try:
            nonce = w3.eth.get_transaction_count(account.address)
            tx = {
                "nonce": nonce,
                "to": to_address,
                "value": amount,
                "gas": 21000,
                "gasPrice": w3.eth.gas_price,
                "chainId": w3.eth.chain_id
            }
            signed_tx = w3.eth.account.sign_transaction(tx, genesis_private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f"Transaction: {tx_hash.hex()}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            print(f"✓ Funded {name} with 100 CFX (block: {receipt['blockNumber']})")
            break
        except Exception as e:
            if "catch up mode" in str(e):
                print(f"  Node still syncing, retry {retry+1}/10...")
                time.sleep(3)
            else:
                raise e
    else:
        print(f"Error: Failed to fund {name} after 10 retries")
        exit(1)

print("\n✓ All accounts funded successfully!")
