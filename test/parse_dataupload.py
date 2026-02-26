from web3 import Web3

w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

# DataUpload 事件签名
event_sig = 'DataUpload(bytes32,uint256,uint256)'
topic0 = w3.keccak(text=event_sig).hex()
da_entrance = '0x6Fefa456504C11B38444Cd66F9D3291270D58CB2'

print(f'查询合约地址: {da_entrance}')
print(f'事件签名哈希: {topic0}\n')

logs = w3.eth.get_logs({
    'fromBlock': 0,
    'toBlock': 'latest',
    'address': da_entrance,
    'topics': [topic0]
})

print(f'找到 {len(logs)} 个 DataUpload 事件\n')

for i, log in enumerate(logs[:10]):
    print(f'=== 事件 {i+1} ===')
    print(f'区块号: {log["blockNumber"]}')
    print(f'交易哈希: {log["transactionHash"].hex()}')
    
    # 解析 data (非indexed参数都在data中)
    data_bytes = log['data']
    
    # dataRoot (32 bytes)
    data_root = '0x' + data_bytes[0:32].hex()
    
    # epoch (32 bytes)
    epoch = int.from_bytes(data_bytes[32:64], 'big')
    
    # quorumId (32 bytes)
    quorum_id = int.from_bytes(data_bytes[64:96], 'big')
    
    print(f'Data Root: {data_root}')
    print(f'Epoch: {epoch}')
    print(f'Quorum ID: {quorum_id}')
    print()

# 统计
print(f'\n=== 统计信息 ===')
print(f'总 DataUpload 事件数: {len(logs)}')

if len(logs) > 0:
    epochs = set()
    quorums = set()
    data_roots = []

    for log in logs:
        data_bytes = log['data']
        data_root = '0x' + data_bytes[0:32].hex()
        epoch = int.from_bytes(data_bytes[32:64], 'big')
        quorum_id = int.from_bytes(data_bytes[64:96], 'big')
        epochs.add(epoch)
        quorums.add(quorum_id)
        data_roots.append(data_root)

    print(f'涉及的 Epoch: {sorted(epochs)}')
    print(f'涉及的 Quorum ID: {sorted(quorums)}')
    print(f'\n最近 5 个上传的 Data Root:')
    for dr in data_roots[-5:]:
        print(f'  {dr}')
else:
    print('⚠️  未找到任何 DataUpload 事件')
    print('提示: 这可能意味着：')
    print('  1. test-client 还未开始上传数据')
    print('  2. disperser 还未处理数据上传请求')
    print('  3. 检查 disperser 和 test-client 日志确认数据提交流程')
