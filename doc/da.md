
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
   │  3. 配对验证: e(aggSig, G2) == e(hash, aggPK)
   ▼
7. 确认
   DAEntrance: 存储 _verifiedErasureCommitment[identifier] = commitment
```

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

### 4.1 da.rs (内部合约 0x0888...0003)

**存储布局:**

| Slot | 名称 | 说明 |
|------|------|------|
| 0 | currentEpoch | 当前 epoch |
| 1 | quorumCountByEpoch | 每个 epoch 的 quorum 数量 |
| 2 | signers | 签名者注册状态 |
| 3 | signerSocket | 签名者 gRPC 地址 |
| 4 | registrations | epoch 注册状态 |
| 5 | signerPublicKeys | 签名者公钥 (G1: 2 + G2: 4) |
| 6 | epochQuorums | 每个 epoch/quorum 的签名者列表 |
| 7 | allSigners | 所有签名者数组 |

**核心函数:**

```rust
// 获取聚合公钥 (用于验证签名)
fn get_agg_pk_g1(epoch, quorum_id, bitmap) -> (G1Point, total, hit)

// 获取 quorum 中的签名者
fn get_quorum(epoch, quorum_id) -> Vec<Address>

// 注册新签名者
fn register_signer(detail, signature)

// 注册下一个 epoch
fn register_next_epoch(signature)

// 确定 epoch 的 quorum
fn finalize_epoch()
```

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
配对验证:
  e(aggSig, G2) == e(H, aggPK)

实际使用优化公式 (防止 rogue key 攻击):
  gamma = keccak256(H || sig || pkG1 || pkG2) mod r
  e(sig + γ*pkG1, -G2) * e(H + γ*G1, pkG2) == 1
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
