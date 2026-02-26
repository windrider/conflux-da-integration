from web3 import Web3

w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

# DAEntrance 合约地址
da_entrance_address = '0x6Fefa456504C11B38444Cd66F9D3291270D58CB2'

print('=== Conflux DA 合约部署验证 ===\n')
print(f'验证合约: DAEntrance')
print(f'合约地址: {da_entrance_address}\n')

try:
    # 获取合约字节码
    code = w3.eth.get_code(da_entrance_address)
    code_hex = code.hex()
    
    # 判断是否部署成功
    if code_hex == '0x' or len(code_hex) <= 2:
        print(f'❌ 状态: 未部署 (bytecode 为空)')
        print('\n提示: 检查 conflux-da-contract 容器日志确认部署过程')
    else:
        code_size = (len(code_hex) - 2) // 2  # 去掉 '0x' 前缀，每 2 个字符 = 1 byte
        print(f'✅ 状态: 已部署')
        print(f'字节码长度: {code_size} bytes')
        print(f'字节码前 66 字符: {code_hex[:66]}...')
        print('\n✅ DAEntrance 合约部署验证通过')

except Exception as e:
    print(f'❌ 查询失败: {e}')
    print('\n提示: 检查 Conflux 链是否正常运行，RPC 端口 8545 是否可访问')
