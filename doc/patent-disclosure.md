# 专利交底书

## 发明名称

一种两阶段哈希的数据可用性采样方法

**A Two-Stage Hashing Based Data Availability Sampling Method**

## 1. 技术领域

本发明涉及区块链和分布式存储技术领域，具体涉及一种基于两阶段哈希计算的数据可用性采样方法及系统，用于激励去中心化存储网络中的节点持续存储数据。

# 技术方案简述

本发明提出一种两阶段哈希的数据可用性采样方法，采用"本地计算-主动提交"的工作模式。存储节点在本地独立完成两阶段哈希计算：第一阶段仅基于元数据计算行级哈希值，无需访问存储数据，实现快速筛选；第二阶段将真实存储数据纳入哈希计算，确保节点必须持有数据才能通过验证。存储节点主动提交满足难度阈值的采样点至链上智能合约，无需等待外部请求触发，有效解决了现有方案对节点响应率的依赖问题，兼顾验证效率与防作弊安全性。

This invention proposes a two-stage hashing based data availability sampling method with a "local computation and proactive submission" working mode. Storage nodes independently complete two-stage hash computation locally: the first stage computes row-level hash values using only metadata without accessing stored data, enabling fast filtering; the second stage incorporates actual stored data into the hash computation, ensuring that nodes must possess the data to pass verification. Storage nodes proactively submit sampling points meeting the difficulty threshold to on-chain smart contracts without waiting for external requests, effectively solving the dependency on node response rates in existing solutions, achieving both verification efficiency and anti-cheating security.

## 2. 背景技术

### 2.1 以往技术的构成

现有数据可用性系统通常由存储节点、验证合约和数据编码器组成。存储节点持有编码数据，验证合约通过挑战-响应机制或随机采样验证节点的数据持有情况。

### 2.2 以往技术的工作说明

**数据可用性（Data Availability, DA）**：在区块链和分布式系统中，数据可用性指的是确保网络中的数据能够被任何参与者访问和验证。当用户提交数据到链上时，需要保证这些数据被正确存储并且在需要时可以被获取。

**数据可用性采样（Data Availability Sampling, DAS）**：一种验证数据可用性的技术方案。通过随机采样部分数据并结合纠删码编码，可以在不下载全部数据的情况下，以高置信度判断数据是否可用。DAS 的核心思想是：如果多次随机采样都能成功获取数据，则可以概率性地认为完整数据是可用的。

**DA 系统需要解决的两个核心问题**：

1. **数据正确性验证**：验证存储节点收到的数据是否与原始数据一致、是否完整。通常通过纠删码编码、密码学承诺和签名聚合等技术实现。

2. **数据持久存储激励**：通过经济激励机制，鼓励存储节点在数据发布后继续长期保存数据。由于验证过程本身可能不提供奖励，节点可能在验证完成后删除数据以节省存储空间，因此需要额外的激励机制。

**以 Ethereum Danksharding 为代表的现有 DAS 方案**：

Ethereum Danksharding 是目前最具代表性的数据可用性采样方案，其解决上述两个问题的方式如下：

**数据正确性验证**：
1. 原始数据经 Reed-Solomon 纠删码编码，扩展为原始大小的 2 倍
2. 使用 KZG 多项式承诺生成数据证明，便于验证数据正确性
3. 编码后的数据分发到 P2P 网络中的各个节点
4. 轻节点通过 VRF（可验证随机函数）随机选择采样位置，向网络请求对应的数据分片
5. 若多次采样都成功获取到数据，则以高置信度（如 99%+）判定数据可用

**数据持久存储激励**：
Danksharding 本身没有内置的存储激励机制，而是依赖外部因素：
- Rollup 操作员有动力保存数据（因为需要响应挑战）
- 验证者有责任义务存储数据（但没有直接奖励）
- 数据仅需保存约 18 天（短期可用性）

**现有方案的局限性**：

1. **网络传输开销大**：每次采样都需要从 P2P 网络请求数据，采样 N 次意味着 N 次网络请求，网络带宽成为性能瓶颈

2. **缺乏直接的存储激励**：Danksharding 主要解决轻节点的验证问题，但没有内置机制激励存储节点长期保存数据。节点可能在数据发布后删除数据以节省存储空间，导致数据长期可用性无法保证

3. **采样粒度固定**：采样位置由 VRF 随机选取，缺乏分层筛选机制，无法根据元数据预先过滤不必要的采样点

4. **概率分布不均匀**：采用单一随机数决定采样结果，某些数据分片可能因运气问题长期无法被采样验证

综上所述，现有 DAS 方案主要解决轻节点的数据可用性验证问题，但在存储激励、网络效率和采样均匀性方面存在不足。

### 2.3 现有技术问题

1. **性能问题**：传统的数据可用性采样需要频繁读取存储数据进行验证，导致大量磁盘 I/O 操作，系统吞吐量低。

2. **作弊风险**：节点可能仅存储元数据（如 Merkle 根）而不存储真实数据，通过伪造证明获取奖励。

3. **公平性问题**：难以设计一个既能防止作弊、又能公平分配奖励的采样机制，使得存储更多数据的节点获得相应的激励。

4. **验证成本高**：链上合约需要验证每个提交的证明，复杂的验证逻辑导致 Gas 消耗过高。

## 3. 发明内容

### 3.1 发明目的

本发明旨在提供一种两阶段哈希的分层数据可用性采样挖矿方法，解决现有技术中性能低、易作弊、验证成本高的问题，实现高效、安全、公平的数据可用性验证和激励机制。

### 3.2 技术方案

本发明提出一种基于**两阶段哈希计算**的分层采样方法，将数据可用性验证分为两个阶段：

#### 3.2.1 第一阶段：基于元数据的行级快速筛选

**输入参数**：
- `sampleSeed`：全局采样种子，由区块哈希生成（`blockhash(nextSampleHeight - 1)`）
- `epoch`：数据提交的纪元编号
- `quorumId`：数据分片组标识
- `dataRoot`：编码数据的 Merkle 根
- `lineIndex`：行索引（范围 0 到 BLOB_ROW × NUM_COSET - 1）

**计算公式**：
```
lineQuality = Keccak256(sampleSeed, epoch, quorumId, dataRoot, lineIndex)
```

**技术特点**：
- 仅依赖元数据，无需读取真实存储数据
- 利用哈希函数的均匀分布特性，快速计算所有负责行的 lineQuality
- 通过与难度阈值比较，预筛选出候选行，减少后续 I/O 操作

#### 3.2.2 第二阶段：包含真实数据的子行级精确采样

**输入参数**：
- `lineQuality`：第一阶段计算得到的行质量值
- `sublineIndex`：子行索引（范围 0 到 SUBLINES - 1）
- `data`：从存储中读取的真实编码数据块（大小为 32 × BLOB_COL / SUBLINES 字节）

**计算公式**：
```
dataQuality = Keccak256(lineQuality, sublineIndex, data)
quality = lineQuality + dataQuality
```

**技术特点**：
- 真实数据 `data` 参与哈希计算，确保节点必须持有数据才能计算正确的 quality
- 继承第一阶段的随机性，扩展到子行级别的细粒度采样
- 最终 quality 值与难度阈值 `podasTarget` 比较，满足 `quality ≤ podasTarget` 则获得奖励

#### 3.2.3 Subline 细分设计

本发明将每行数据细分为多个子行（subline），每个子行独立计算 dataQuality：

**细分方式**：
- 每行包含 BLOB_COL 个元素（典型值 1024）
- 每行切分为 SUBLINES 个子行（典型值 32）
- 每个子行包含 BLOB_COL / SUBLINES 个元素（典型值 32 个元素，1KB 数据）

**设计优势**：
- **多次中奖机会**：每行有 SUBLINES 次独立的采样机会，而非仅有一次
- **概率分布更均匀**：即使 lineQuality 较大，某个子行的 dataQuality 可能足够小使最终 quality 满足要求
- **避免运气偏差**：防止某些行因 lineQuality 不佳而完全没有中奖机会
- **细粒度采样**：提高对数据存储的覆盖率和验证精度

#### 3.2.4 完整的采样流程

**链下节点侧（本地计算 + 按需提交）**：
1. 监听链上的 `ErasureCommitmentVerified` 事件，获取已验证的数据提交信息
2. 轮询合约获取当前采样轮的 `sampleSeed` 和 `podasTarget`
3. **第一阶段（无 I/O）**：对节点负责的所有行计算 lineQuality，仅使用元数据
4. **第二阶段（本地 I/O）**：对每行的每个子行：
   - 从本地存储读取对应的数据块 `data`
   - 计算 `dataQuality` 和最终 `quality`
   - 若 `quality ≤ podasTarget`，构造包含 Merkle 证明的 `SampleResponse`
5. **按需提交**：仅将“中奖”的 `SampleResponse` 提交到链上合约

**关键设计：本地计算模式**：
- 与现有 DAS（轻节点每次采样都需网络请求）不同，本发明采用“本地遍历计算 + 结果提交”模式
- 节点在本地完成所有计算，仅将满足条件的采样点提交到链上
- 大幅减少网络数据传输量，避免网络带宽成为瓶颈

**链上合约侧**：
1. 接收节点提交的 `SampleResponse`
2. 验证采样点唯一性：`identifier = Keccak256(sampleSeed, epoch, quorumId, lineIndex, sublineIndex)`，确保未重复提交
3. **重新计算 quality**：
   - 计算 `lineQuality = Keccak256(sampleSeed, epoch, quorumId, dataRoot, lineIndex)`
   - 计算 `dataQuality = Keccak256(lineQuality, sublineIndex, data)`
   - 验证 `lineQuality + dataQuality == rep.quality`
4. 验证 Merkle 证明，确保 `data` 来自真实的编码数据
5. 检查 `quality ≤ podasTarget` 和其他约束条件（epoch 有效期等）
6. 验证通过后，发放奖励到节点账户

### 3.3 技术效果

相比现有技术（如 Celestia、Ethereum Danksharding 的 DAS 方案），本发明具有以下优势：

1. **本地计算模式，大幅减少网络传输**：
   - 现有 DAS：轻节点每次采样都需从网络请求数据，采样 N 次 = 网络请求 N 次
   - 本发明：存储节点在本地遍历计算，仅将“中奖”的采样点提交到链上
   - 效果：网络数据传输量减少 99% 以上，避免网络带宽成为性能瓶颈

2. **两阶段过滤，极致 I/O 优化**：
   - 第一阶段仅依赖元数据，无需磁盘 I/O
   - 第二阶段仅对本节点负责的行读取数据
   - 最终仅“中奖”的子行需要构造证明并提交
   - 实现三层过滤：节点分配 → 元数据筛选 → 质量阈值筛选

3. **Subline 细分设计，概率分布更均匀**：
   - 每行细分为多个子行，每个子行独立计算 dataQuality
   - 每行有 SUBLINES 次独立的中奖机会（典型值 32 次）
   - quality = lineQuality + dataQuality，两个随机变量相加使分布更均匀
   - 避免某些行因 lineQuality 不佳而完全没有中奖机会

4. **安全防作弊**：
   - 真实数据必须参与第二阶段哈希计算，节点无法仅通过元数据伪造证明
   - 链上合约重新计算 quality 并验证 Merkle 证明，确保数据真实性
   - 采样点唯一性标识防止重复提交

5. **公平激励**：
   - 哈希函数的均匀分布特性保证伪随机公平性
   - 存储更多数据的节点有更多采样机会，获得相应的奖励概率
   - 动态难度调整机制平衡激励与成本

6. **高效链上验证**：
   - 链上验证仅需两次哈希计算 + Merkle 证明验证，Gas 消耗低
   - 计算逻辑简单清晰，适合智能合约实现

7. **可扩展性**：
   - 分层结构支持灵活调整行数、子行数等参数
   - 难度阈值可根据网络状态动态调整

## 4. 具体实施方式

### 4.1 系统架构

本发明涉及的系统包括以下组件：

1. **智能合约**：部署在区块链上，负责：
   - 管理采样种子和难度参数
   - 验证节点提交的采样响应
   - 发放挖矿奖励

2. **存储节点（DA Node）**：分布式网络中的存储节点，负责：
   - 存储编码后的数据
   - 执行两阶段哈希挖矿
   - 提交采样响应到链上

3. **数据编码器（Encoder）**：将原始数据进行纠删码编码，生成冗余数据和 Merkle 树

### 4.2 关键参数定义

| 参数名称 | 说明 | 典型值 |
|---------|------|--------|
| `BLOB_ROW` | 每个 blob 的行数 | 1024 |
| `BLOB_COL` | 每个 blob 的列数（元素数） | 1024 |
| `NUM_COSET` | Coset 数量（编码冗余） | 3 |
| `SUBLINES` | 每行切分的子行数 | 32 |
| `samplePeriod` | 采样周期（区块数） | 100 |
| `podasTarget` | 难度阈值 | 可调整，初始值约为 2^256 / 128 |
| `epochWindowSize` | Epoch 有效期窗口 | 100 |

### 4.3 第一阶段详细流程

#### 4.3.1 采样种子生成

智能合约在每个采样周期开始时，生成新的采样种子：

```solidity
function _updateSampleRound() internal {
    if (block.number >= nextSampleHeight) {
        currentSampleSeed = blockhash(nextSampleHeight - 1);
        nextSampleHeight += samplePeriod;
        sampleRound += 1;
        
        // 难度调整
        podasTarget = _adjustPodasTarget();
        roundSubmissions = 0;
    }
}
```

**关键点**：
- 使用 `blockhash(nextSampleHeight - 1)` 作为随机源，不可预测且不可操纵
- 每个采样轮有唯一的 `sampleSeed`

#### 4.3.2 行级质量值计算

节点获取当前 `sampleSeed` 后，对自己负责的行计算 lineQuality：

```rust
// 伪代码
for each assigned_line in node.assigned_slices {
    let line_quality = keccak256(
        sample_seed,
        epoch,
        quorum_id,
        data_root,
        assigned_line.line_index
    );
    
    // 初步判断是否可能满足难度要求
    // 注意：此处无法直接判断最终 quality，但可以作为启发式筛选
    candidates.push(LineCandidate {
        line_index: assigned_line.line_index,
        line_quality,
    });
}
```

**优化策略**：
- 可以设置阈值，只对 `lineQuality` 较小的行进入第二阶段
- 但实际实现中通常对所有负责的行都进行第二阶段计算（因为 dataQuality 不可预测）

### 4.4 第二阶段详细流程

#### 4.4.1 数据读取与子行切分

对每个候选行，节点从本地存储读取完整行数据（1024 个 BLS 字段元素，每个 32 字节）：

```rust
// 伪代码
let row_data = slice_db.read(epoch, quorum_id, line_index); // 32 KB
let subline_size = row_data.len() / SUBLINES; // 32 KB / 32 = 1 KB per subline

for subline_index in 0..SUBLINES {
    let subline_data = &row_data[subline_index * subline_size..(subline_index + 1) * subline_size];
    
    // 计算 dataQuality
    let data_quality = keccak256(line_quality, subline_index, subline_data);
    let quality = line_quality + data_quality;
    
    if quality <= podas_target {
        // 构造采样响应
        let response = build_sample_response(
            sample_seed, epoch, quorum_id, 
            line_index, subline_index,
            quality, data_root, subline_data
        );
        submit_to_chain(response);
    }
}
```

**关键点**：
- 必须读取真实存储的数据才能计算 `dataQuality`
- 每个子行独立计算，提高采样覆盖率

#### 4.4.2 Merkle 证明构造

节点需要为提交的子行数据构造 Merkle 证明，证明该数据属于已验证的 `dataRoot`：

1. **子行数据哈希**：计算子行数据的 Merkle 叶子节点（根据 0g-storage 规则）
2. **Blob 内证明**：从叶子节点到 blobRoot 的 Merkle 路径
3. **Blob 间证明**：3 个 blobRoots 到 dataRoot 的证明

### 4.5 链上验证流程

#### 4.5.1 采样响应数据结构

```solidity
struct SampleResponse {
    bytes32 sampleSeed;      // 采样种子
    uint64 epoch;            // 数据纪元
    uint64 quorumId;         // 分片组 ID
    uint32 lineIndex;        // 行索引
    uint32 sublineIndex;     // 子行索引
    uint quality;            // 质量值
    bytes32 dataRoot;        // 数据 Merkle 根
    bytes32[3] blobRoots;    // 3 个 blob 的根
    bytes32[] proof;         // Merkle 证明
    bytes data;              // 子行数据（1 KB）
}
```

#### 4.5.2 验证逻辑

```solidity
function submitSamplingResponse(SampleResponse memory rep) external {
    // 1. 基础检查
    bytes32 identifier = keccak256(abi.encodePacked(
        rep.sampleSeed, rep.epoch, rep.quorumId, 
        rep.lineIndex, rep.sublineIndex
    ));
    require(!_submittedDASampling[identifier], "Duplicated submission");
    _submittedDASampling[identifier] = true;
    
    require(rep.sampleSeed == currentSampleSeed, "Unmatched sample seed");
    require(rep.quality <= podasTarget, "Quality not reached");
    require(commitmentExists(rep.dataRoot, rep.epoch, rep.quorumId), "Unrecorded commitment");
    require(rep.epoch + epochWindowSize >= currentEpoch, "Epoch has stopped sampling");
    
    // 2. 重新计算 quality
    uint lineQuality = uint256(keccak256(abi.encodePacked(
        rep.sampleSeed, rep.epoch, rep.quorumId, 
        rep.dataRoot, rep.lineIndex
    )));
    uint dataQuality = uint256(keccak256(abi.encodePacked(
        lineQuality, rep.sublineIndex, rep.data
    )));
    require(lineQuality + dataQuality == rep.quality, "Incorrect quality");
    
    // 3. 验证 Merkle 证明
    bytes32 lineRoot = calculateLineRoot(rep.data);
    uint64 blobIndex = rep.lineIndex / BLOB_ROW;
    bytes32 blobRoot = rep.blobRoots[blobIndex];
    uint64 merklePosition = (rep.lineIndex % BLOB_ROW) * SUBLINES + rep.sublineIndex;
    verifyBlobRoot(lineRoot, blobRoot, rep.proof, merklePosition);
    verifyDataRoot(rep.blobRoots, rep.dataRoot);
    
    // 4. 发放奖励
    address beneficiary = DA_SIGNERS.getQuorumRow(rep.epoch, rep.quorumId, rep.lineIndex);
    uint reward = activedReward / rewardRatio;
    _asyncTransfer(beneficiary, reward);
    
    emit DAReward(beneficiary, sampleRound, rep.epoch, rep.quorumId, 
                  rep.dataRoot, rep.quality, rep.lineIndex, rep.sublineIndex, reward);
}
```

**验证要点**：
- **采样点唯一性**：通过 `identifier` 映射防止重复提交
- **Quality 正确性**：合约重新计算，确保节点没有伪造
- **数据真实性**：Merkle 证明验证确保数据来自已承诺的编码数据
- **时间有效性**：只有在有效期内的 epoch 可以参与采样

### 4.6 动态难度调整

智能合约根据上一轮的实际提交数调整难度阈值：

```solidity
function _adjustPodasTarget() internal view returns (uint podasTargetNext) {
    uint targetDelta;
    if (roundSubmissions > targetRoundSubmissions) {
        // 提交过多，提高难度（降低阈值）
        targetDelta = (roundSubmissions - targetRoundSubmissions) * podasTarget / targetRoundSubmissions / 8;
        podasTargetNext = podasTarget - targetDelta;
    } else {
        // 提交过少，降低难度（提高阈值）
        targetDelta = (targetRoundSubmissions - roundSubmissions) * podasTarget / targetRoundSubmissions / 8;
        podasTargetNext = podasTarget + targetDelta;
    }
    
    // 上限保护
    if (podasTargetNext > MAX_PODAS_TARGET) {
        podasTargetNext = MAX_PODAS_TARGET;
    }
}
```

**调整策略**：
- 每次调整幅度为偏差的 1/8，避免剧烈波动
- 设置最大阈值 `MAX_PODAS_TARGET = 2^256 / 128`，防止难度过低

## 5. 有益效果

本发明通过两阶段哈希的分层采样机制，实现了以下技术效果：

### 5.1 性能优势

- **减少 I/O 开销**：第一阶段无需读取数据，快速筛选候选行，避免大量无效的磁盘访问
- **并行计算友好**：两阶段的计算逻辑简单，适合并行处理，可利用多核 CPU 加速
- **链上验证高效**：验证逻辑仅需两次哈希 + Merkle 路径验证，Gas 消耗低（约 100-200K Gas）

### 5.2 安全保障

- **强制数据持有**：第二阶段必须使用真实数据计算 dataQuality，节点无法通过仅存储元数据获取奖励
- **防重放攻击**：采样点唯一性标识确保每个 (sampleSeed, epoch, quorumId, lineIndex, sublineIndex) 组合只能提交一次
- **防伪造证明**：链上合约重新计算 quality 并验证 Merkle 证明，确保数据真实性

### 5.3 公平性

- **伪随机公平**：哈希函数的均匀分布特性保证每个采样点获得奖励的概率相等
- **存储激励正相关**：节点存储的数据越多，负责的行越多，获得奖励的机会越大
- **动态平衡**：难度自适应调整机制维持激励与成本的经济平衡

### 5.4 可扩展性

- **参数灵活**：行数、子行数、采样周期、难度阈值等参数可根据网络需求调整
- **模块化设计**：两阶段逻辑独立，可分别优化或替换哈希算法
- **兼容性好**：适用于各种纠删码编码方案和 Merkle 树结构

## 6. 附图说明

### 图1：系统架构图
（建议包含：智能合约、存储节点、数据编码器、区块链之间的交互关系）

### 图2：两阶段哈希计算流程图
（建议包含：第一阶段 lineQuality 计算 → 候选行筛选 → 第二阶段 dataQuality 计算 → 最终 quality 判断）

### 图3：链上验证流程图
（建议包含：接收 SampleResponse → 唯一性检查 → 重新计算 quality → Merkle 证明验证 → 发放奖励）

### 图4：动态难度调整机制图
（建议包含：提交数监控 → 难度调整算法 → 新阈值应用）

## 7. 权利要求（初稿）

### 主权利要求

1. 一种两阶段哈希的分层数据可用性采样挖矿方法，其特征在于，包括以下步骤：

   （1）生成采样种子：智能合约在每个采样周期使用区块哈希生成全局采样种子 `sampleSeed`；

   （2）第一阶段行级筛选：存储节点对其负责的每一行数据，仅依据元数据计算行级质量值：
   ```
   lineQuality = Hash(sampleSeed, epoch, quorumId, dataRoot, lineIndex)
   ```
   其中，Hash 为 Keccak256 哈希函数；

   （3）第二阶段子行挖矿：对候选行的每个子行，从本地存储读取真实数据块 `data`，计算子行质量值和最终质量值：
   ```
   dataQuality = Hash(lineQuality, sublineIndex, data)
   quality = lineQuality + dataQuality
   ```

   （4）难度判断：若 `quality ≤ podasTarget`，则构造包含 Merkle 证明的采样响应并提交到链上；

   （5）链上验证：智能合约重新计算 quality、验证 Merkle 证明、检查采样点唯一性，验证通过后发放奖励。

### 从属权利要求

2. 根据权利要求 1 所述的方法，其特征在于，所述采样种子 `sampleSeed` 通过区块哈希函数生成：
   ```
   sampleSeed = blockhash(nextSampleHeight - 1)
   ```
   其中，`nextSampleHeight` 为下一个采样周期的目标区块高度。

3. 根据权利要求 1 所述的方法，其特征在于，所述第一阶段的行级筛选无需读取存储数据，仅依赖元数据进行快速计算。

4. 根据权利要求 1 所述的方法，其特征在于，所述第二阶段的子行挖矿必须读取真实存储数据才能计算正确的 `dataQuality`，从而确保节点真实持有数据。

5. 根据权利要求 1 所述的方法，其特征在于，所述采样点唯一性标识为：
   ```
   identifier = Hash(sampleSeed, epoch, quorumId, lineIndex, sublineIndex)
   ```
   智能合约通过映射表记录已提交的 identifier，防止重复提交。

6. 根据权利要求 1 所述的方法，其特征在于，所述难度阈值 `podasTarget` 根据上一轮实际提交数动态调整：
   - 若实际提交数超过目标值，则降低阈值（提高难度）；
   - 若实际提交数低于目标值，则提高阈值（降低难度）。

7. 根据权利要求 1 所述的方法，其特征在于，所述 Merkle 证明包括：
   - 子行数据到 blob 根的 Merkle 路径；
   - blob 根到 dataRoot 的聚合证明。

8. 一种实现权利要求 1 所述方法的系统，包括：
   - 智能合约模块：管理采样种子、难度参数，验证采样响应，发放奖励；
   - 存储节点模块：执行两阶段哈希挖矿，提交采样响应；
   - 数据编码模块：对原始数据进行纠删码编码并生成 Merkle 树。

## 8. 实施例变化

本发明的技术方案可根据实际需求进行以下变化：

1. **哈希算法替换**：可使用 SHA256、BLAKE2 等其他密码学哈希函数替代 Keccak256。

2. **分层层数扩展**：可增加更多层次的哈希计算，实现三阶段或多阶段筛选。

3. **难度调整策略**：可采用更复杂的动态调整算法（如 PID 控制器）以更精确地控制提交率。

4. **奖励分配机制**：可结合节点的历史表现、存储时长等因素设计更复杂的奖励函数。

5. **并行优化**：第一阶段和第二阶段的计算可利用 GPU、FPGA 等硬件加速。

---

## 附录：术语解释

- **Data Availability (DA)**：数据可用性，确保区块链或分布式系统中的数据可被网络节点访问和验证。
- **Erasure Coding**：纠删码，一种数据冗余编码技术，可在部分数据丢失时恢复原始数据。
- **Merkle Tree**：Merkle 树，一种哈希树结构，用于高效验证大数据集中的部分数据。
- **Keccak256**：一种密码学哈希函数，输出 256 位哈希值，具有均匀分布和雪崩效应特性。
- **PoDA (Proof of Data Availability)**：数据可用性证明，节点通过提供有效的数据采样证明获取奖励的共识机制。
- **Quorum**：分片组，将存储网络划分为多个组，每个组负责部分数据的存储和验证。

## temp1：以往的工作说明（强调验证数据可用性）
在区块链和分布式系统中，数据可用性（Data Availability，简称DA）指的是确保网络中的数据能够被任何参与者访问和验证。
数据可用性问题的核心诉求为，需向区块链全网证明拟上链的汇总交易数据对应有效交易集合，且该证明过程无需全网所有节点全量下载上述交易数据；完整的交易数据是节点独立完成区块有效性验证的必要前提，然而要求所有节点全量下载并校验全部交易数据，会形成区块链系统扩容的核心性能瓶颈。解决数据可用性问题的根本目标，在于实现非全量下载存储交易数据的网络参与者，亦可获取完整的交易数据以完成区块与交易的有效性验证，即在兼顾验证完整性的同时，降低全网节点的存储与带宽开销，突破区块链扩容的技术约束。

为实现上述目标，需采用一种新的数据组织与存储模式：将待上链数据分散存储于多个节点而非集中存储，使得轻量级节点可仅从部分存储节点获取数据样本即可完成验证。具体而言，在用户向区块链提交待上链数据的全流程中，需确保数据完成合规持久化存储，且在有效性验证、状态恢复等关键业务场景下可被网络节点可靠获取。目前行业内普遍采用分布式存储架构承载用户提交的待上链数据：首先将原始数据进行纠删码冗余编码处理，使得仅需部分数据分片即可恢复完整原始数据；随后将编码后的数据分片分布式存储在多个去中心化部署的存储节点上，依托节点去中心化部署提升数据存储的容错性与整体可用性。

然而，分布式存储架构的引入带来了新的挑战：由于分布式网络的开放性特征，数据的存储、传输与访问流程易遭受恶意攻击，亦存在存储节点主动作恶的风险，诸如数据篡改、分片丢失、拒绝数据访问等行为均会直接导致数据可用性失效。因此，数据可用性（DA）系统需构建一套标准化的存储验证机制，对存储节点的数存状态进行精准校验，核心需验证存储节点持久化的目标数据与用户提交的原始数据是否保持一致性、完整性。
针对前述数据可用性问题，现有技术中已提出数据可用性采样（Data Availability Sampling，简称DAS）方案，其核心设计目标为：在不向网络中任一节点施加过量存储与带宽压力的前提下，实现对链上数据可用性的高效校验，同时降低节点参与验证的门槛，保障网络去中心化特性。
DAS方案的核心执行逻辑为分布式轻量采样验证：网络中的每个节点，无论是否为质押节点，均无需全量下载并存储链上待验证数据，仅需从完整数据集的全部分片（含原始分片与冗余分片）中，随机选取极小规模的数据子集（即采样分片）进行下载与校验。基于概率统计原理，若节点能够成功下载并验证所选取的全部随机样本，即可高置信度地确认完整数据集均处于可用状态，无需通过全量数据校验完成可用性判定，大幅降低了单个节点的资源开销。
    以以太坊Danksharding方案为典型代表，现有DAS技术已形成标准化的全流程执行体系，其数据预处理与采样验证环节具备明确的技术实现路径。
具体而言，在数据预处理阶段，首先对用户提交的原始待上链数据采用Reed-Solomon纠删码进行编码处理，通过注入冗余信息生成冗余分片，使编码后的数据集满足“仅需部分有效分片即可恢复完整原始数据”的容错特性，为后续轻量采样验证提供基础支撑；同时，基于编码后的数据分片构建多项式模型，采用KZG多项式承诺技术生成对应的数据证明（即全局承诺值），并将该承诺值锚定至区块链区块头，形成不可篡改的完整性校验基准。完成编码与承诺生成后，编码后的原始分片及冗余分片将分布式分发至P2P网络中的各存储节点，依托分布式架构提升数据存储的容错性与可访问性。
进入DAS验证阶段，网络中的轻节点无需全量下载存储上述数据分片，仅通过可验证随机函数（Verifiable Random Function，VRF）生成不可预测且可验证的随机采样位置，基于该位置向P2P网络中的对应存储节点发起数据分片请求。轻节点接收存储节点返回的数据分片后，结合区块头中的KZG承诺值完成分片完整性与归属权校验；若经过多次独立随机采样均能成功获取有效数据分片并通过校验，则基于概率统计原理高置信度判定完整数据集处于可用状态，无需通过全量数据下载校验完成可用性确认，大幅降低了单个节点的存储与带宽资源开销，同时兼顾验证效率与可靠性。

### 3.2 本发明内容的工作说明
发明要点（技术特征）
应清楚、明确地对该发明创造的技术方案进行描述，是体现发明的思路。利用上述技术方案的一个具体实施的例子，要详细的描述技术方案的实施过程。应该结合相关的流程图、原理框图、电路图、时序图等进行说明（除非实在不能提供附图时）。

区别于现有DAS方案采用的"请求-响应"验证模式，本发明提出一种基于两阶段哈希计算的数据可用性采样方法，采用"本地计算-主动提交"的工作模式。

在本发明的技术方案中，用户提交的原始数据首先经过编码器进行纠删码冗余编码处理，编码后的数据被划分为多个数据分片，分布式存储于网络中的各存储节点。在每个采样周期内，存储节点从链上智能合约获取当前的随机种子（sampleSeed）和难度阈值（podasTarget），随后在本地遍历其所负责存储的全部数据分片，独立执行两阶段哈希计算：

**第一阶段（元数据筛选）**：仅基于行级元数据与随机种子计算行级质量值lineQuality，该阶段无需访问实际存储数据，可实现对候选采样点的快速筛选。

**第二阶段（数据验证）**：将每一行数据细分为若干子行，针对每个子行将真实存储数据纳入哈希计算，得到子行级质量值dataQuality，该机制确保存储节点必须持有真实数据方可通过验证。

**质量值判定**：最终质量值quality = lineQuality + dataQuality，与难度阈值podasTarget进行比较，满足quality ≤ podasTarget条件的采样点即为有效采样点，对应的存储节点可获得相应奖励。

存储节点将满足条件的采样结果提交至链上智能合约，由智能合约执行完整的验证流程：根据提交的采样数据重新计算lineQuality和dataQuality，验证所提交的quality值的正确性；验证Merkle证明，确保所提交的数据确实来源于已承诺的编码数据；检查采样点唯一性标识，防止重复提交。全部验证通过后，智能合约向存储节点发放奖励。

此外，链上智能合约还具备动态难度调整机制，可根据网络实际参与情况自适应调整难度阈值：若上一轮实际提交数超过目标值，则降低podasTarget（即提高采样难度）；若上一轮实际提交数低于目标值，则提高podasTarget（即降低采样难度），以此维持系统激励与成本的动态平衡。

#### 具体实施例

以下结合具体实施例详细说明本发明技术方案的实施过程。

实施例参数设置如表1所示：

表1 实施例参数设置

| 参数名称 | 参数说明 | 参数取值 |
|----------|----------|----------|
| BLOB_ROW | 每个数据块的行数 | 1024 |
| BLOB_COL | 每行的元素数 | 1024 |
| NUM_COSET | 编码冗余倍数 | 3 |
| SUBLINES | 每行划分的子行数 | 32 |
| samplePeriod | 采样周期（区块数） | 100 |
| podasTarget | 初始难度阈值 | 2^256 / 128 |

具体实施步骤如下：

步骤一：数据编码与分发

用户将原始数据提交至数据编码器，编码器采用Reed-Solomon纠删码对数据进行编码处理，生成具有3倍冗余度的编码数据。同时，基于编码后的数据构建Merkle树，生成数据根dataRoot。编码完成后，数据分片被分发至各存储节点，每个存储节点负责存储部分行数据。存储节点对接收的数据进行完整性验证并签名，聚合签名后提交至链上完成数据注册。链上智能合约触发ErasureCommitmentVerified事件，标志数据已完成正确性验证。

步骤二：采样种子生成

智能合约在每个采样周期（每100个区块）开始时，基于区块哈希计算新的采样种子，计算公式为：

    sampleSeed = blockhash(nextSampleHeight - 1)    —————— 公式(1)

并根据上一轮的实际提交情况调整难度阈值podasTarget。

步骤三：存储节点获取采样参数

存储节点持续监听链上的ErasureCommitmentVerified事件，获取已验证数据的相关信息（包括dataRoot、epoch、quorumId等）。同时，存储节点从智能合约获取当前采样周期的采样种子sampleSeed和难度阈值podasTarget。

步骤四：第一阶段——行级质量值计算

存储节点遍历其所负责存储的所有行数据。对于每一行，仅基于元数据计算行级质量值，计算公式为：

    lineQuality = Keccak256(sampleSeed, epoch, quorumId, dataRoot, lineIndex)    —————— 公式(2)

该阶段完全基于元数据计算，无需读取存储数据，计算速度极快。由于最终质量值quality = lineQuality + dataQuality，若lineQuality已远超过难度阈值，则该行可提前排除，无需进入第二阶段计算。

步骤五：第二阶段——子行级质量值计算

对于每一候选行，存储节点从本地存储读取完整行数据（大小为32KB），并将其切分为32个子行，每个子行大小为1KB。针对每个子行，计算数据质量值和最终质量值，计算公式为：

    dataQuality = Keccak256(lineQuality, sublineIndex, sublineData)    —————— 公式(3)
    quality = lineQuality + dataQuality    —————— 公式(4)

随后判断是否满足难度要求：quality ≤ podasTarget。若满足条件，则该子行为有效采样点。

步骤六：构造采样响应并提交

对于满足quality ≤ podasTarget条件的子行，存储节点构造采样响应数据结构，包含采样种子、行索引、子行索引、质量值、子行数据及Merkle证明等信息，并将采样响应提交至链上智能合约。

步骤七：链上验证与奖励发放

智能合约接收采样响应后，执行以下验证流程：

    （1）参数一致性验证：验证提交的sampleSeed与当前采样周期的采样种子一致；
    （2）质量值验证：重新计算lineQuality和dataQuality，验证提交的quality值正确且满足quality ≤ podasTarget；
    （3）数据真实性验证：验证Merkle证明，确保提交的子行数据来源于已承诺的编码数据；
    （4）唯一性验证：检查采样点唯一性标识，防止同一采样点被重复提交；
    （5）时间窗口验证：验证epoch仍在有效采样窗口内。

全部验证通过后，智能合约向对应的存储节点发放采样奖励。

### 3.3 简述本发明的效果

本发明提供一种基于两阶段哈希计算的数据可用性采样方法，采用"本地计算-主动提交"的工作模式。存储节点在本地独立计算行级质量值（lineQuality）与子行级质量值（dataQuality），求和得到最终质量值（quality），仅将满足quality ≤ podasTarget条件的子行主动提交至链上智能合约。与现有DAS方案采用的"请求-响应"验证模式相比，本发明具有以下显著的有益效果：

（1）消除了对存储节点响应率的依赖，系统性能不再受限于网络延迟与节点响应能力

现有DAS方案中，采样验证者（轻节点或验证者）需向存储节点发起数据分片请求，等待存储节点响应并返回数据后方可执行后续验证。该模式使得系统性能高度依赖于存储节点的响应速度与响应率：若存储节点响应延迟较高或选择性响应请求，将直接导致采样验证效率下降；在网络延迟较大的场景下，请求-响应往返时间将显著增加，影响整体验证效率。本发明采用"本地计算-主动提交"模式，存储节点根据链上智能合约发布的采样种子与难度阈值，在本地独立完成两阶段哈希计算，主动提交满足条件的采样证明，全程无需等待外部请求触发。该设计使得系统性能不再受限于网络延迟与存储节点响应能力，有效提升了采样验证的稳定性与高效性。

（2）显著减轻验证者负担，计算任务均衡分布于分布式存储节点

现有DAS方案中，采样验证者需主动发起大量采样请求，维护请求列表、管理响应超时、执行KZG承诺验证等工作，导致验证者需承担较重的计算与通信开销。在高并发场景下，大量验证者同时发起采样请求会对存储节点形成请求压力，同时验证者也需处理大量响应消息，容易形成性能瓶颈。本发明将采样计算任务分散至各存储节点，由存储节点在本地独立完成两阶段哈希计算，仅将满足难度要求的子行提交至链上智能合约。由于难度阈值的控制作用，提交的采样证明数量受限，验证者（链上智能合约）仅需被动接收并验证提交的采样证明，无需主动发起请求，显著减轻了验证者的计算与通信负担。同时，计算任务的均衡分布使得系统天然支持大规模并行计算，显著提升了系统的可扩展性。

（3）保障了激励机制的公平性，存储数据越多获得奖励的概率越大

现有DAS方案中，轻节点发起的采样请求是随机的且不可预测，存储节点无法提前预知哪些数据分片会被采样，因此存储节点缺乏明确的经济激励来长期存储数据，容易导致"搭便车"问题：部分存储节点可能仅在接收到采样请求时临时从其他节点获取数据分片并返回，而不真实存储数据。本发明采用PoDA（Proof of Data Availability）挖矿机制，存储节点通过计算两阶段哈希来寻找满足难度要求的子行，必须持有真实存储数据才能通过第二阶段的dataQuality计算（需将子行数据纳入哈希），确保存储节点无法通过伪造数据获取收益。由于质量值计算公式中包含了随机种子、epoch、quorumId、dataRoot、lineIndex、sublineIndex、sublineData等参数，且采用加法聚合方式计算最终质量值，使得存储节点存储的子行数量与获得有效采样点的概率呈正相关：存储的子行越多，寻找到满足quality ≤ podasTarget条件的子行概率越大，从而获得奖励的机会越高。该机制保障了激励的公平性，鼓励存储节点真实存储更多数据，促进了网络数据存储容量的增长。

综上所述，本发明通过创新的两阶段哈希计算与主动提交模式，有效解决了现有DAS方案对节点响应率的依赖问题，显著减轻了验证者负担，并构建了公平合理的激励机制，具有重要的技术价值与应用前景。





