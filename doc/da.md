
# Conflux DA (Data Availability) 系统文档

## 1. 系统概述

Conflux DA 是一个基于 BLS 签名和 KZG 承诺的数据可用性解决方案。系统通过多个 DA 节点分布式存储数据，并通过密码学证明确保数据的完整性和可用性。

### 1.1 核心组件

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  Disperser  │────▶│  DA Nodes   │
└─────────────┘     └─────────────┘     └─────────────┘
                          │                    │
                          ▼                    │
                    ┌─────────────┐            │
                    │   Encoder   │            │
                    └─────────────┘            │
                          │                    │
                          ▼                    ▼
                    ┌─────────────────────────────┐
                    │     Conflux Blockchain      │
                    │  ┌─────────┐  ┌──────────┐  │
                    │  │DAEntrance│  │da.rs     │  │
                    │  │ (EVM)   │  │(Internal)│  │
                    │  └─────────┘  └──────────┘  │
                    └─────────────────────────────┘
```

| 组件 | 职责 |
|------|------|
| **Client** | 提交原始数据 |
| **Disperser** | 协调编码、签名收集、链上提交 |
| **Encoder** | 纠删码编码 + KZG 承诺生成 |
| **DA Nodes** | 存储数据切片、验证并签名 |
| **DAEntrance.sol** | EVM 业务合约，处理数据提交和验证 |
| **da.rs** | 内部合约 (0x0888...0003)，管理签名者和公钥 |

---

## 2. 完整流程

### 2.1 流程图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           DA 数据提交流程                                  │
└──────────────────────────────────────────────────────────────────────────┘

1. 编码阶段
   Client ──[原始数据]──▶ Disperser ──[原始数据]──▶ Encoder
                                                      │
   ┌──────────────────────────────────────────────────┘
   │  返回:
   │  - storage_root (Merkle 根)
   │  - erasure_commitment (KZG 承诺)
   │  - encoded_slices[1024] (编码后的行数据 + 证明)
   ▼
2. 链上注册
   Disperser ──[submitOriginalData(dataRoots)]──▶ DAEntrance.sol
                                                      │
   ┌──────────────────────────────────────────────────┘
   │  触发事件: DataUpload(dataRoot, epoch, quorumId)
   ▼
3. 获取 Quorum
   Disperser ──[getQuorum(epoch, quorumId)]──▶ da.rs
                                                  │
   ┌──────────────────────────────────────────────┘
   │  返回: 1024 个签名者地址 (round-robin 分配)
   ▼
4. 签名请求
   Disperser ──[gRPC: 发送负责的行]──▶ DA Node 1
             ──[gRPC: 发送负责的行]──▶ DA Node 2
             ──[gRPC: 发送负责的行]──▶ DA Node 3
                                          │
   ┌──────────────────────────────────────┘
   │  每个 DA Node:
   │  1. 验证 AMT 证明 (多项式承诺)
   │  2. 验证 Merkle 证明 (数据完整性)
   │  3. 签名: sig = sk * hash(storage_root, epoch, quorum_id, commitment)
   ▼
5. 签名聚合 (链下)
   Disperser:
   - aggSig = sig1 + sig2 + sig3 + ...
   - bitmap = [1,1,1,0,...] (标记谁签名了)
   
6. 链上验证
   Disperser ──[submitVerifiedCommitRoots(aggSig, bitmap, ...)]──▶ DAEntrance.sol
                                                                        │
                                                                        ▼
                                              DAEntrance ──[getAggPkG1(bitmap)]──▶ da.rs
                                                                        │
   ┌────────────────────────────────────────────────────────────────────┘
   │  验证:
   │  1. 根据 bitmap 聚合公钥: aggPK = pk1 + pk2 + pk3 + ...
   │  2. 检查签名比例: hit / total >= 2/3
   │  3. 配对验证 (防 rogue key 攻击):
   │     γ = keccak256(sig, pkG1, pkG2, hash) mod r
   │     e(sig + γ*pkG1, -G2) * e(hash + γ*G1, pkG2) == 1
   ▼
7. 确认
   DAEntrance: 存储 _verifiedErasureCommitment[identifier] = commitment
   触发事件: ErasureCommitmentVerified(dataRoot, epoch, quorumId)
```

### 2.2 DA Sampling 与奖励挖矿流程（与数据提交并行）

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      DA Sampling 挖矿流程（并行）                           │
└──────────────────────────────────────────────────────────────────────────┘

1. DA Node 监听链上事件
   DA Node ──[监听 ErasureCommitmentVerified 事件]──▶ DAEntrance.sol
                                                         │
   ┌──────────────────────────────────────────────────────┘
   │  获取:
   │  - dataRoot (数据标识)
   │  - epoch (epoch 编号)
   │  - quorumId (quorum 标识)
   │  - commitment (已验证的纠删码承诺)
   ▼
2. 读取 DA Sampling 参数
   DA Node ──[sampleTask()]──▶ DAEntrance.sol
                                  │
   ┌──────────────────────────────┘
   │  返回:
   │  - sampleSeed (当前 round 的随机种子)
   │  - podasTarget (PoDA 难度目标)
   │  - sampleRound (采样轮次)
   ▼
3. 本地 PoDA 挖矿
   DA Node:
   - 基于 sampleSeed、dataRoot、epoch、quorumId 计算哈希
   - 遍历自己负责的行索引 (lineIndex) 和子索引 (sublineIndex)
   - 计算 quality = keccak256(sampleSeed || dataRoot || epoch || quorumId || lineIndex || sublineIndex)
   - 当 quality <= podasTarget 时，找到有效解
   
4. 生成采样证明
   DA Node:
   - 读取本地存储的切片数据 (row data)
   - 生成 AMT 证明 (row commitment + Merkle 证明)
   - 构造 SampleResponse:
     * dataRoot, epoch, quorumId
     * sampleSeed, quality
     * lineIndex, sublineIndex
     * row (切片数据)
     * amt_proof (AMT 树证明)
     * merkle_proof (Merkle 树证明)
   
5. 提交采样响应到链上
   DA Node ──[submitSamplingResponse(SampleResponse)]──▶ DAEntrance.sol
                                                             │
   ┌─────────────────────────────────────────────────────────┘
   │  验证:
   │  1. quality <= podasTarget (难度检查)
   │  2. sampleSeed == currentSampleSeed (种子匹配)
   │  3. commitmentExists(dataRoot, epoch, quorumId) (数据已验证)
   │  4. epoch + epochWindowSize >= currentEpoch (时间窗口检查)
   │  5. verify_amt_proof (AMT 树证明验证)
   │  6. verify_merkle_proof (Merkle 树证明验证)
   ▼
6. 发放奖励
   DAEntrance:
   - 查询 DA_SIGNERS.getQuorumRow(epoch, quorumId, lineIndex) 获取受益人地址
   - 计算奖励: reward = activedReward / rewardRatio + donation
   - 异步转账给受益人 (PullPayment 模式)
   - 触发事件: DAReward(beneficiary, sampleRound, epoch, quorumId, dataRoot, quality, lineIndex, sublineIndex, reward)
   
7. DA Node 领取奖励
   DA Node ──[withdrawPayments()]──▶ DAEntrance.sol (PullPayment)
                                        │
   ┌───────────────────────────────────┘
   │  将累积的奖励转账到 DA Node 账户
   ▼
   DA Node 收到奖励
```

**关键要点:**

- **sampleSeed 的来源**: 合约在每一轮采样开始时，根据固定高度的区块哈希生成随机种子：
  - 设 `samplePeriod` 为采样周期（区块数），`nextSampleHeight` 为下一轮采样高度；当 `block.number >= nextSampleHeight` 时，进入新一轮采样，执行 
    - `currentSampleSeed = blockhash(nextSampleHeight - 1)`
    - `nextSampleHeight += samplePeriod`
  - DA Node 通过 `sampleTask()` 获取的 `sampleSeed` 实际上就是当前轮的 `currentSampleSeed`，并在提交 `SampleResponse` 时要求 `rep.sampleSeed == currentSampleSeed`。
- **采样点唯一性**: 合约使用 `identifier = keccak256(sampleSeed, epoch, quorumId, lineIndex, sublineIndex)` 唯一标识一个采样点；每个采样点只能成功挖矿一次，重复提交会被 `_submittedDASampling[identifier]` 拦截。
- **quality 计算与难度**:
  - 行级质量: `lineQuality = keccak256(sampleSeed, epoch, quorumId, dataRoot, lineIndex)`
  - 子行级质量: `dataQuality = keccak256(lineQuality, sublineIndex, data)`
  - 最终质量: `quality = lineQuality + dataQuality`，合约在 `verify()` 中重算并要求 `lineQuality + dataQuality == rep.quality`，且 `rep.quality <= podasTarget` 才视为“挖中”。
- **数据有效性与时间窗口**: 只有已经通过 `submitVerifiedCommitRoots` 确认的 `(dataRoot, epoch, quorumId)` 才能被采样；同时要求 `rep.epoch < currentEpoch` 且 `currentEpoch <= rep.epoch + epochWindowSize`，限制可挖历史范围。
- **奖励归属与记账方式**: 合约通过 `DA_SIGNERS.getQuorumRow(epoch, quorumId, lineIndex)` 将奖励归属到该行对应的 signer 地址，奖励金额来自 `activedReward / rewardRatio + donation`，采用 PullPayment 模式异步记账，最终由 DA Node 调用 `withdrawPayments()` 提现。
- **触发条件**: DA Node 通过监听 `ErasureCommitmentVerified` 事件，得知有新的已验证数据可以挖矿。
- **挖矿机制**: PoDA (Proof of Data Availability) - 通过暴力搜索找到满足 `quality <= podasTarget` 的 (lineIndex, sublineIndex) 组合。
- **动态难度**: `podasTarget` 会根据每轮提交数量自动调整，类似 PoW 难度调整。
- **奖励来源**: 
  - `activedReward`: 从用户提交 `submitOriginalData` 时支付的费用中积累
  - `totalDonations`: 外部捐赠池
- **防作弊**: 链上会验证完整的 AMT + Merkle 证明，确保 DA Node 真实存储了数据。
- **时间窗口**: 只有在 `[epoch, epoch + epochWindowSize)` 范围内的数据才能参与挖矿，过期数据不再奖励。

#### 2.2.1 DA Node 挖矿视角（链下流程）

1. **监听与准备**：
   - 监听 `ErasureCommitmentVerified` 事件，将对应 `(epoch, quorumId, dataRoot)` 在本地标记为 `VERIFIED`，并停止对该 blob 的后续签名服务。
   - 周期性调用 `sampleTask()/sampleRange()`，获取当前轮的 `sampleSeed`、`podasTarget` 以及可挖的 `epoch` 区间。
   - 从 `da.rs` 同步本节点在各个 `(epoch, quorumId)` 下的 `AssignedSlices`（本节点负责的行索引集合），并确保对应行数据已缓存在本地 `slice_db` 中。
2. **第一阶段（行级筛选）**：
   - 在可挖 `epoch` 区间内，对每个候选行计算 `lineQuality = keccak256(sampleSeed, epoch, quorumId, dataRoot, lineIndex)`。
   - 仅对本节点负责的行（`AssignedSlices`）且本地有数据的行构建 `LineCandidate`，作为第二阶段的输入。
3. **第二阶段（子行挖矿）**：
   - 从 `slice_db` 读取行数据，按 `NUM_SUBLINES` 切分为多个子行。
   - 对每个 `(lineIndex, sublineIndex)` 计算 `dataQuality = keccak256(lineQuality, sublineIndex, data)` 和 `quality = lineQuality + dataQuality`，筛选出满足 `quality <= podasTarget` 的采样点。
   - 为每个命中点构造 `SampleResponse`，包含：`epoch, quorumId, dataRoot, lineIndex, sublineIndex, quality, sample_seed`，以及子行 Merkle 证明、行 Merkle 证明和 `blob_roots`，确保链上可重放验证。
4. **上链提交与领奖**：
   - Submitter 在提交前再次通过 `commitmentExists(dataRoot, epoch, quorumId)` 确认该 blob 已在链上完成 erasure commitment 验证。
   - 调用 `submitSamplingResponse(SampleResponse)` 将本次挖矿结果提交给 `DAEntrance`；成功后合约发出 `DAReward` 事件，并将奖励记入 PullPayment 余额。
   - DA Node 可按策略（例如累计到一定金额或定期）调用 `withdrawPayments()`，将链上累积奖励提取到本地账户。
---

## 3. 数据结构

### 3.1 编码输出 (EncodedBlob)

```rust
pub struct EncodedBlob {
    pub erasure_commitment: G1Affine,    // 全局 KZG 承诺
    pub storage_root: [u8; 32],          // Merkle 树根
    pub encoded_data: Vec<u8>,           // 原始编码数据
    pub encoded_slice: Vec<EncodedSlice>, // 1024 个切片
}

pub struct EncodedSlice {
    pub index: usize,
    pub amt: EncodedSliceAMT,      // AMT 证明
    pub merkle: EncodedSliceMerkle, // Merkle 证明
}

pub struct EncodedSliceAMT {
    pub index: usize,
    pub commitment: G1Affine,      // 行承诺
    pub row: BlobRow,              // 行数据 + 证明
}

pub struct BlobRow {
    pub index: usize,
    pub row: Vec<Scalar>,          // 1024 个数据点
    pub proof: Proof,              // AMT 证明 (商多项式 + 低度测试)
    pub high_commitment: G1Affine, // 高阶多项式承诺
}


// AMT 证明结构: 每层 (兄弟承诺, 商多项式证明)
pub struct Proof(Vec<(G1Affine, G1Affine)>);
```
提交到链上的数据结构
```go
submissions[i] = da_entrance.IDAEntranceCommitRootSubmission{
    DataRoot:          s.DataRoot,           // 1. 数据 Merkle 根 (32 bytes)
    Epoch:             s.Epoch,              // 2. Epoch 编号
    QuorumId:          s.QuorumId,           // 3. Quorum ID
    ErasureCommitment: {X, Y},               // 4. KZG 承诺 (G1 点)
    QuorumBitmap:      s.QuorumBitmap,       // 5. 哪些行被签名 (位图)
    AggPkG2:           {X, Y},               // 6. 聚合公钥 (G2 点)
    Signature:         {X, Y},               // 7. 聚合签名 (G1 点)
}
```
### 3.2 AMT 树结构

```
                    C_root (erasure_commitment)
                   /                           \
              C_01                              C_02
             /    \                            /    \
          C_1      C_2                      C_3      C_4
         / \       / \                      / \       / \
       ...  ...  ...  ...                 ...  ...  ...  ...
       /                                                    \
    Row_0                                              Row_1023
```

- 每行是多项式 P(x) 在不同点的求值
- 行承诺通过二叉树聚合到根承诺
- 验证时使用商多项式证明行属于全局多项式

---

## 4. 合约配合

### 4.1 da.rs 内置合约详解 (0x0888...0003)

da.rs 是 **Conflux DA 系统的核心组件**，作为 Conflux 区块链的内置合约实现。它完全使用 Rust 编写，替代了 0G 链中的 Solidity 预编译合约，提供签名者管理、公钥存储和 BN254 签名验证功能。

**源码位置**: `blockchain/conflux-rust/crates/execution/executor/src/internal_contract/impls/da.rs` (约 1275 行)

---

#### 4.1.1 存储布局

```
da.rs 使用 Solidity 兼容的存储布局，所有槽位基于合约地址计算:
base_slot = keccak256(0x0888000000000000000000000000000000000003)
```

| Slot | 类型 | 说明 |
|------|------|------|
| 0 | `uint256` | **currentEpoch** - 当前 epoch 编号 |
| 1 | `mapping(uint256 => uint256)` | **quorumCountByEpoch** - 每个 epoch 的 quorum 数量 |
| 2 | `mapping(address => bool)` | **signers** - 签名者注册状态 |
| 3 | `mapping(address => bytes)` | **signerSocket** - 签名者 gRPC 地址 (3槽: data0, data1, length) |
| 4 | `mapping(address => mapping(uint256 => bool))` | **registrations** - 签名者的 epoch 注册状态 |
| 5 | `mapping(address => uint256[6])` | **signerPublicKeys** - 公钥存储 [G1.x, G1.y, G2.x0, G2.x1, G2.y0, G2.y1] |
| 6 | `mapping(uint256 => mapping(uint256 => address[]))` | **epochQuorums** - epoch/quorum 的签名者列表 (1024个) |
| 7 | `address[]` | **allSigners** - 所有已注册签名者数组 |
| 16 | `uint256` | **EpochBlocks** - epoch 长度 (默认 100 区块) |

---

#### 4.1.2 BN254 密码学实现

da.rs 实现了完整的 BN254 (bn128) 椭圆曲线密码学操作:

```rust
// 坐标转换
fn u256_pair_to_g1(x, y) -> G1      // U256 对转 G1 点
fn u256_quad_to_g2(x0, x1, y0, y1) -> G2  // U256 四元组转 G2 点

// 哈希到曲线 (Try-and-Increment 方法)
fn map_to_curve(digest: [u8; 32]) -> G1 {
    // BN254 曲线方程: y² = x³ + 3
    // 反复尝试 x 值直到找到有效曲线点
    for _ in 0..100 {
        let y_squared = x³ + 3 (mod p)
        let y = y_squared^((p+1)/4) (mod p)  // sqrt 利用 p ≡ 3 (mod 4)
        if y² == y_squared {
            return (x, y)
        }
        x = x + 1
    }
}

// 计算 gamma (防 rogue key 攻击)
fn compute_gamma(hash, signature, pkG1, pkG2) -> Fr {
    // γ = keccak256(hash || sig || pkG1 || pkG2) mod r
    let gamma_hash = keccak256(serialize(hash, sig, pkG1, pkG2));
    Fr::from_slice(gamma_hash)
}
```

---

#### 4.1.3 只读函数 (View Functions)

| 函数 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `epoch_number()` | - | `U256` | 获取当前 epoch |
| `get_quorum(epoch, quorum_id)` | epoch, quorumId | `Vec<Address>` | 获取 quorum 中 1024 个签名者地址 |
| `get_quorum_row(epoch, quorum_id, row)` | epoch, quorumId, rowIndex | `Address` | 获取特定槽位的签名者 |
| `get_signer(addresses)` | `Vec<Address>` | `Vec<SignerDetail>` | 获取签名者详情 (地址, socket, 公钥) |
| `is_signer(address)` | address | `bool` | 检查是否已注册签名者 |
| `quorum_count(epoch)` | epoch | `U256` | 获取 epoch 的 quorum 数量 |
| `registered_epoch(signer, epoch)` | signer, epoch | `bool` | 检查签名者是否注册了某 epoch |
| **`get_agg_pk_g1(epoch, quorum_id, bitmap)`** | epoch, quorumId, bitmap | `(G1Point, total, hit)` | **核心: 聚合公钥计算** |

**get_agg_pk_g1 详解** (最关键的函数):

```rust
pub fn get_agg_pk_g1(epoch, quorum_id, bitmap) -> (G1Point, total, hit) {
    let quorum_signers = get_quorum(epoch, quorum_id);  // 获取 1024 个地址
    let mut hit_count = 0;
    let mut agg_point: Option<G1> = None;
    let mut added_signers: HashSet<Address> = HashSet::new();  // 去重!
    
    for (i, signer_addr) in quorum_signers.iter().enumerate() {
        // 检查 bitmap 中第 i 位是否为 1
        let is_set = (bitmap[i/8] & (1 << (i%8))) != 0;
        if !is_set { continue; }
        
        hit_count += 1;  // 每个 set 的 bit 都计数
        
        // 去重: 同一 signer 可能占多个 slot，但公钥只加一次
        if added_signers.contains(signer_addr) {
            continue;  // hit_count 已递增，但公钥不重复加
        }
        added_signers.insert(*signer_addr);
        
        // 读取并聚合公钥
        let (g1_x, g1_y) = read_signer_pk_g1(signer_addr);
        let point = G1::from(AffineG1::new(g1_x, g1_y));
        agg_point = Some(agg_point + point);
    }
    
    return (agg_point, total, hit_count);
}
```

---

#### 4.1.4 状态变更函数 (State-Changing Functions)

**1. register_signer** - 注册新签名者

```rust
pub fn register_signer(signer_detail: SignerDetail, signature: G1Point) {
    // 1. 验证调用者就是要注册的签名者
    require!(params.sender == signer_detail.address);
    
    // 2. BN254 签名验证 (防止伪造公钥)
    //    消息: keccak256(address || chainId || "0G_BN254_Pubkey_Registration")
    let msg_hash = keccak256(sender || chainId || "0G_BN254_Pubkey_Registration");
    let H = map_to_curve(msg_hash);
    let γ = compute_gamma(H, signature, pkG1, pkG2);
    
    // 配对验证: e(sig + γ*pkG1, -G2) * e(H + γ*G1, pkG2) == 1
    require!(pairing_check(signature, pkG1, pkG2, H, γ));
    
    // 3. 存储公钥 (6 个 U256: G1.x, G1.y, G2.x0, G2.x1, G2.y0, G2.y1)
    store_pubkey(signer_addr, pkG1, pkG2);
    
    // 4. 存储 socket 地址 (gRPC 端点)
    store_socket(signer_addr, socket);
    
    // 5. 标记为已注册 + 加入 allSigners 数组
    signers[signer_addr] = true;
    allSigners.push(signer_addr);
    
    // 6. 触发 NewSigner 事件
    emit NewSigner(signer_addr, pkG1, pkG2);
}
```

**2. register_next_epoch** - 注册下一个 epoch

```rust
pub fn register_next_epoch(signature: G1Point) {
    // 1. 验证调用者已是签名者
    require!(signers[sender]);
    
    // 2. 计算 next_epoch
    let next_epoch = currentEpoch + 1;
    
    // 3. 签名验证
    //    消息: keccak256(sender || next_epoch || chainId)
    let msg_hash = keccak256(sender || next_epoch || chainId);
    require!(verify_signature(signature, msg_hash, sender_pubkeys));
    
    // 4. 标记注册状态
    registrations[sender][next_epoch] = true;
}
```

**3. finalize_epoch** - 构建新 epoch 的 Quorum

```rust
pub fn finalize_epoch() {
    // 1. 检测是否应该进入新 epoch
    let expected_epoch = block_number / EpochBlocks;  // 默认 100 区块一个 epoch
    if expected_epoch == currentEpoch { return; }
    require!(expected_epoch == currentEpoch + 1);
    
    // 2. 收集已注册的签名者
    let mut registered = Vec::new();
    for signer in allSigners {
        if registrations[signer][expected_epoch] {
            registered.push(signer);
        }
    }
    
    // 3. Round-Robin 分配 1024 个槽位
    if registered.is_empty() {
        quorumCount[expected_epoch] = 0;
    } else {
        for i in 0..1024 {
            epochQuorums[expected_epoch][0][i] = registered[i % registered.len()];
        }
        quorumCount[expected_epoch] = 1;
    }
    
    // 4. 更新 currentEpoch
    currentEpoch = expected_epoch;
}
```

**4. update_socket** - 更新 socket 地址

```rust
pub fn update_socket(new_socket: String) {
    require!(signers[sender]);
    store_socket(sender, new_socket);
    emit SocketUpdated(sender, new_socket);
}
```

---

#### 4.1.5 与 0G 原版的对比

| 方面 | 0G (Solidity Precompile) | Conflux (Rust Internal Contract) |
|------|--------------------------|----------------------------------|
| **语言** | Solidity + Go (预编译) | 纯 Rust |
| **合约地址** | 0x...1000 | 0x0888...0003 |
| **BN254 操作** | 调用 EVM 预编译合约 (0x06-0x08) | 直接使用 `bn` crate |
| **存储方式** | EVM storage | `get_system_storage` / `set_system_storage` |
| **签名验证** | 无 (信任模式) | **完整实现** (防 rogue key) |
| **事件** | Solidity events | 自定义 `SolidityEventTrait` |
| **交易类型** | EIP-1559 | Legacy (Type 0) |

#### 4.1.6 Signer 注册与 Slot 2/4/6/7 的关系

下面这几个 slot 都与 signer 注册生命周期相关：

- **Slot 2 `signers`**: `mapping(address => bool)`，标记某个地址是否已经成功注册为 DA signer。
- **Slot 4 `registrations`**: `mapping(address => mapping(uint256 => bool))`，记录某个 signer 在某个 epoch 上是否完成了“参与该 epoch”的签名登记。
- **Slot 7 `allSigners`**: `address[]`，保存所有已经注册成功的 signer 地址，用于在构建新 epoch 的 quorum 时进行遍历。
- **Slot 6 `epochQuorums`**: `mapping(uint256 => mapping(uint256 => address[]))`，在 `finalize_epoch` 时，将某个 epoch 下完成注册的 signer 按 round-robin 写入这里，形成用于签名分配的 1024 槽位数组。

整体流程可以分成三步：

1. **Signer 首次注册 (`register_signer`) 阶段**
   - 校验调用者 `params.sender` 必须等于 `SignerDetail` 中提供的地址。
   - 使用带 gamma 的 BLS 配对验证校验提交的公钥和签名是否匹配。
   - 验证通过后：
     - 在 **Slot 2 `signers[sender]` 写入 `true`**，标记该地址为已注册 signer。
     - 将 signer 的 G1/G2 公钥写入 **Slot 5 `signerPublicKeys`** 对应的 6 个槽位（供后续验证和聚合使用）。
     - 将 socket 地址写入 **Slot 3 `signerSocket`** 的 3 个槽位。
     - 如果此前不是 signer，则把该地址追加进 **Slot 7 `allSigners` 数组** 末尾，并递增数组长度。

2. **Signer 为下一个 epoch 登记 (`register_next_epoch`) 阶段**
   - 先从 **Slot 2 `signers`** 读取 `params.sender` 的状态，要求已经是注册 signer。
   - 从 **Slot 5 `signerPublicKeys`** 读取该 signer 的 G1/G2 公钥，结合链上环境 (`chain_id`)、`next_epoch` 等计算消息哈希，做一次带 gamma 的 BLS 验证，确保是本人在为“参与 next_epoch”签名。
   - 验证通过后，在 **Slot 4 `registrations[sender][next_epoch]` 写入 `true`**，表示该 signer 声明自己要参与下一个 epoch 的 DA 签名。
   - 此时不会修改 quorum 相关的 slot，真正的 quorum 构建留给 `finalize_epoch` 调用。

3. **构建新 epoch quorum (`finalize_epoch`) 阶段**
   - 根据当前块高和 `EpochBlocks` 计算 `expected_epoch`，并检查它是否等于 `currentEpoch + 1`。
   - 从 **Slot 7 `allSigners`** 读出所有 signer 地址，然后逐个检查 **Slot 4 `registrations[signer][expected_epoch]`**，把在该 epoch 上登记过的 signer 收集到 `registered_signers` 列表。
   - 如果 `registered_signers` 为空：
     - 将 **Slot 1 `quorumCountByEpoch[expected_epoch]` 置为 0**，表示该 epoch 下没有 quorum，`epochQuorums` 不写入。
   - 否则：
     - 在 **Slot 6 `epochQuorums[expected_epoch][0]`** 下创建一个长度为 1024 的动态数组：
       - 长度写入数组头部（用于后续 `get_quorum` / `get_quorum_row` 读取）。
       - 依次将 `registered_signers[i % registered_signers.len()]` 写入 0..1023 槽位，实现 round-robin 分配，使每个 signer 负责若干行。
     - 再将 **Slot 1 `quorumCountByEpoch[expected_epoch]` 设为 1**，表示该 epoch 有 1 个 quorum（`quorum_id = 0`）。
     - 最后更新 **Slot 0 `currentEpoch`** 为 `expected_epoch`。

有了以上关系，配合前文的 `get_quorum` / `get_quorum_row` / `get_agg_pk_g1`：
- `get_quorum`/`get_quorum_row` 只读 **Slot 6 + Slot 1**，拿到某个 epoch/quorum 下 1024 个 signer 槽位。
- `get_agg_pk_g1` 先调用 `get_quorum` 获取 signer 地址，再从 **Slot 5** 取出这些 signer 的 G1 公钥，根据 bitmap 去重后做椭圆曲线加法聚合，同时统计命中槽位数 `hit_count`，最终输出给 `DAEntrance` 做阈值判断和 BLS 验证。

这样可以把 signer 从“注册自己”“声明参与某个 epoch”，一路串联到“被分配到 quorum 槽位、参与聚合公钥与聚合签名验证”的完整链路。

### 4.2 DAEntrance.sol (EVM 合约)

**核心函数:**


```solidity
// 提交数据根，触发 DataUpload 事件
function submitOriginalData(bytes32[] memory _dataRoots) external payable

// 提交聚合签名验证
function submitVerifiedCommitRoots(CommitRootSubmission[] memory _submissions) external

// 提交数据结构
struct CommitRootSubmission {
    bytes32 dataRoot;
    uint256 epoch;
    uint256 quorumId;
    BN254.G1Point erasureCommitment;
    bytes quorumBitmap;
    BN254.G2Point aggPkG2;
    BN254.G1Point signature;
}
```

### 4.3 合约调用关系

```
User
  │
  ▼
DAEntrance.sol ◄──────────────────────────────────────┐
  │                                                    │
  │ submitOriginalData()                               │
  │   └─ emit DataUpload(dataRoot, epoch, quorumId)   │
  │                                                    │
  │ submitVerifiedCommitRoots()                        │
  │   └─ DA_SIGNERS.getAggPkG1(epoch, quorumId, bitmap)
  │        │                                           │
  │        ▼                                           │
  │     da.rs (0x0888...0003)                         │
  │        │                                           │
  │        └─ 返回 (aggPkG1, total, hit)              │
  │                                                    │
  │   └─ 验证 hit/total >= 阈值                        │
  │   └─ 配对验证签名                                  │
  │   └─ 存储 _verifiedErasureCommitment               │
  │                                                    │
  └────────────────────────────────────────────────────┘
```

---

## 5. BLS 签名机制

### 5.1 签名流程

```
DA Node 签名:
  hash = keccak256(storage_root || epoch || quorum_id || erasure_commitment)
  H = MapToCurve(hash)  // 哈希映射到 G1 曲线
  sig = sk * H          // 私钥标量乘法
```

### 5.2 聚合

```
Disperser 聚合签名 (链下):
  aggSig = sig_1 + sig_2 + sig_3 + ...

链上聚合公钥:
  aggPK = pk_1 + pk_2 + pk_3 + ...  (根据 bitmap 去重)
```

### 5.3 验证

```
配对验证 (防止 rogue key 攻击):
  γ = keccak256(sig || pkG1 || pkG2 || hash) mod r
  e(sig + γ*pkG1, -G2) * e(hash + γ*G1, pkG2) == 1

为什么需要 G1 和 G2 两个公钥:
  - aggPkG1: 链上根据 bitmap 聚合计算 (不信任 disperser)
  - aggPkG2: Disperser 提交 (G2 点大，链上聚合代价高)
  - γ 将 G1 绑定进验证，防止伪造 G2 通过验证
```

---

## 6. Quorum 构建

### 6.1 finalize_epoch 流程

```
1. 检测新 epoch: block_number / EpochBlocks > currentEpoch

2. 收集已注册签名者:
   for signer in allSigners:
       if registrations[signer][new_epoch]:
           registered_signers.append(signer)

3. Round-Robin 分配 1024 个槽位:
   for i in 0..1024:
       quorum[i] = signers[i % len(signers)]

4. 更新 currentEpoch
```

### 6.2 示例

```
3 个签名者，1024 个槽位:

slot 0   -> Signer A
slot 1   -> Signer B  
slot 2   -> Signer C
slot 3   -> Signer A  (循环)
slot 4   -> Signer B
...
slot 1023 -> Signer B

每个签名者负责约 341-342 行
```

---

## 7. 关键设计要点

### 7.1 为什么公钥聚合在链上做？

Disperser 不可信！如果让 Disperser 提交聚合公钥：
- 可以伪造 bitmap，谎称更多节点签名
- 提交假的聚合公钥通过验证

解决方案：
- 链上存储每个签名者的公钥
- Disperser 只提交 bitmap
- 链上根据 bitmap 重新计算聚合公钥
- 用链上计算的公钥验证签名

### 7.2 聚合公钥为什么需要去重？

```
Disperser 聚合签名: 按 signer 迭代，天然不重复
链上聚合公钥: 按 bitmap (slot) 迭代，同一 signer 可能占多个 slot

解决: 使用 HashSet 跟踪已添加的 signer，跳过重复
```

### 7.3 hit_count 的意义

```rust
// 链上代码
hit_count += 1;  // 每个 set 的 bit 都计数

if added_signers.contains(signer_addr) {
    continue;    // 公钥聚合去重，但 hit_count 已递增
}
```

- hit_count 表示覆盖了多少个槽位
- total 表示 quorum 总槽位数 (1024)
- 验证: hit / total >= 阈值 (如 2/3)
