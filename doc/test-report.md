# 测试报告
## 1.项目概述
### 1.1 系统介绍

本项目是一个基于 Conflux 区块链的数据可用性（Data Availability, DA）解决方案集成测试环境。系统采用分布式架构，通过纠删码编码、BLS 签名聚合和 KZG 承诺等密码学技术，实现数据的高可用性存储和验证。

#### 核心组件

系统由以下关键组件构成：

1. **Conflux Chain (conflux-chain)**
   - 底层区块链节点，提供 eSpace (EVM 兼容层) 和 Core Space 接口
   - 运行 DAEntrance.sol 智能合约（处理数据提交和验证）
   - 内置 da.rs 内部合约（管理签名者注册和公钥存储）
   - 端口：8545 (eSpace RPC), 12537 (Conflux RPC)

2. **DA Disperser (0g-da-disperser)**
   - 协调数据分发流程的核心服务
   - 负责与 Encoder 通信完成纠删码编码
   - 收集 DA Nodes 的 BLS 签名并进行聚合
   - 向链上提交验证数据和聚合签名
   - gRPC 端口：51001

3. **DA Encoder (0g-da-encoder)**
   - 数据编码服务，支持 GPU 加速
   - 执行纠删码编码（将数据扩展为 1024 个切片）
   - 生成 KZG 承诺和 Merkle 树证明
   - 为每个切片生成 AMT 证明

4. **DA Nodes (0g-da-node x3)**
   - 三节点集群，分布式存储数据切片
   - 验证接收到的数据切片（AMT 证明 + Merkle 证明）
   - 对验证通过的数据进行 BLS 签名
   - 监听链上事件，参与 PoDA 挖矿获取奖励
   - 端口：34001, 34002, 34003

5. **Test Client (0g-da-test-client)**
   - 模拟用户持续提交数据的测试客户端
   - 通过 gRPC 与 Disperser 交互

6. **DA Contract (0g-da-contract)**
   - DAEntrance.sol 智能合约部署服务
   - 管理数据提交、验证和奖励分发逻辑

#### 技术特点

- **纠删码编码**：将原始数据编码为 1024 个切片，支持容错恢复
- **BLS 签名聚合**：多个签名可聚合为单个签名，降低链上验证成本
- **KZG 承诺**：使用多项式承诺确保数据完整性
- **PoDA 挖矿**：Proof of Data Availability 机制激励节点真实存储数据
- **动态难度调整**：根据提交数量自动调整挖矿难度
- **时间窗口验证**：限制数据有效期，防止过期数据被重复提交

#### 部署架构

所有组件通过 Docker Compose 编排，使用共享网络栈（network_mode: "service:conflux-chain"）实现服务间通信。系统支持自动健康检查、依赖管理和故障重启。
### 1.2 测试目的
### 1.3 测试地点

## 2. 测试对象
### 2.1 测试内容
### 2.2 测试环境

本次测试在 Linux 服务器环境中执行，采用 Docker 容器化技术进行系统部署与隔离。测试环境通过 Docker Compose 编排管理，将 DA 系统的各个核心组件（包括 Conflux 区块链节点、DA Disperser、DA Encoder、DA Nodes 集群、智能合约部署服务及测试客户端）分别部署在独立的 Docker 容器中运行。

**网络拓扑特点**：
- 所有容器采用共享网络栈模式（`network_mode: "service:conflux-chain"`），通过 `localhost` 实现容器间的高效通信
- 各组件通过预定义的端口进行服务发现和数据交互，无需额外的网络配置
- 容器之间网络完全互通，支持 gRPC、HTTP/WebSocket 等多种协议通信
- 宿主机通过端口映射可直接访问容器内服务，便于外部监控和调试

**部署优势**：
- **环境隔离**：每个组件在独立容器中运行，避免依赖冲突
- **自动编排**：通过依赖关系定义实现服务的有序启动和健康检查
- **快速部署**：一键启动整个测试环境，支持快速重建和回滚
- **资源管理**：可灵活配置各容器的 CPU、内存和 GPU 资源分配
- **可复现性**：基于镜像的部署方式确保测试环境的一致性和可移植性


#### 硬件环境

| 组件 | 实际配置 |
|------|----------|
| CPU | x86_64 架构，8 核 |
| 内存 | 16GB |
| 存储 | 100GB 可用空间 |
| GPU | NVIDIA GPU（支持 CUDA，用于 Encoder 加速）|
| 网络 | 内网环境，已开放端口：8545, 8546, 12537, 12535, 32323, 34001-34003, 51001 |

#### 软件环境

| 软件 | 版本 |
|------|------|
| 操作系统 | Linux Ubuntu 24.04 |
| Docker | 20.10+ |
| Docker Compose | v2.0+ |
| NVIDIA Container Toolkit | 已配置，用于 GPU 加速 |
| Python | 3.11 |
| Node.js & Yarn | Node 16+ |

#### 区块链配置

**Conflux Chain 配置** (conflux.toml):

| 配置项 | 值 | 说明 |
|--------|-----|------|
| mode | dev | 开发模式，固定出块间隔 |
| dev_block_interval_ms | 1000 | 出块间隔 1 秒 |
| chain_id | 10 | Conflux Core Space 链 ID |
| evm_chain_id | 10 | eSpace (EVM 兼容层) 链 ID |
| target_block_gas_limit | 60,000,000 | 区块 Gas 上限（用于 DA 合约部署） |
| cipda | 0 | DA 功能从区块 0 开始启用 |
| cip90_transition_height | 0 | Type 0 (EIP-155) 交易从区块 0 启用 |
| cip1559_transition_height | 999999999 | 禁用 EIP-1559（需要 PoS） |
| pos_reference_enable_height | 999999999 | 禁用 PoS 共识（单节点环境） |
| node_type | archive | 归档节点模式，保留完整历史 |

**DA 合约地址**:

| 合约 | 地址 |
|------|------|
| DAEntrance.sol | 0x6Fefa456504C11B38444Cd66F9D3291270D58CB2 |
| da.rs (内部合约) | 0x0888000000000000000000000000000000000003 |

#### DA Node 配置

**节点私钥配置** (三节点):

| 节点 | gRPC 端口 | BLS 私钥 | Validator 私钥 | Signer 私钥 | Miner 私钥 |
|------|-----------|----------|----------------|-------------|------------|
| DA Node 1 | 34001 | 11 | 0xac097... | 0x17939... | 0x9549f... |
| DA Node 2 | 34002 | 22 | 0x59c69... | 0x14f2d... | 0x3cebb... |
| DA Node 3 | 34003 | 33 | 0x5de4e... | 0x6c1b5... | 0x8b10e... |

**通用配置**:
- `encoder_params_dir`: "params/" (KZG 参数目录)
- `eth_rpc_endpoint`: "http://localhost:8545/" (eSpace RPC)
- `da_entrance_address`: 0x6Fefa456504C11B38444Cd66F9D3291270D58CB2
- `start_block_number`: 0
- `enable_das`: true (启用 DA Sampling 挖矿)

#### Disperser 配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| grpc-port | 51001 | 对外服务端口 |
| encoder-socket | localhost:34000 | Encoder 服务地址 |
| pull-interval | 30s | 拉取待编码数据间隔 |
| signed-pull-interval | 60s | 拉取已签名数据间隔 |
| finalizer-interval | 20s | 提交验证数据间隔 |
| batch-size-limit | 500 | 单批次最大数据条数 |
| encoding-timeout | 300s | 编码超时时间 |
| chain-gas-limit | 2,000,000 | 单笔交易 Gas 限制 |
| receipt-wait-rounds | 180 | 等待交易确认轮数 |
| use-memory-db | true | 使用内存数据库（测试模式） |

#### 容器网络拓扑

所有容器使用共享网络栈模式 (`network_mode: "service:conflux-chain"`)，通过 localhost 互相访问，端口映射如下：

```
宿主机端口映射:
- 8545  → eSpace RPC (Conflux Chain)
- 8546  → eSpace WebSocket
- 12537 → Conflux RPC
- 12535 → Conflux WebSocket
- 32323 → P2P Network
- 34001 → DA Node 1 gRPC
- 34002 → DA Node 2 gRPC
- 34003 → DA Node 3 gRPC
- 51001 → Disperser gRPC
```

#### 启动依赖关系

```
conflux-chain (健康检查)
    ↓
fund-accounts (账户初始化)
    ↓
0g-da-contract (合约部署)
    ↓
0g-da-node x3 + 0g-da-encoder (并行启动)
    ↓
0g-da-disperser (等待所有 DA Node 健康检查通过)
    ↓
0g-da-test-client (开始测试)
```

#### GPU 加速配置（可选）

如果宿主机安装了 NVIDIA GPU 和 Container Toolkit，Encoder 将自动使用 GPU 加速编码过程：

- 构建时自动检测 CUDA 环境（`check_cuda.sh`）
- 检测成功则编译 CUDA 特性版本
- 容器运行时分配所有可用 GPU (`count: all`)
- 若无 GPU 环境，自动降级为 CPU 模式