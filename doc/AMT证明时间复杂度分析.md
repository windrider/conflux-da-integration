# 聚合默克尔树（AMT）证明生成的时间复杂度分析

## 1. 技术背景

本文档针对基于聚合默克尔树（Aggregated Merkle Tree，简称AMT）的数据可用性证明系统，对其证明生成过程的时间复杂度进行详细分析。

### 1.1 数据结构

原始数据规模为 n×n 个数据元素，其中 n=1024，每个数据元素占用 31 字节。该原始数据经过 Reed-Solomon（RS）纠删编码后，被分布式编码至 3 个独立的陪集（coset）上。每个陪集独立生成对应的 AMT 证明结构。

数据结构定义如下：

```rust
pub struct EncodedBlobAMT(
    [HalfBlob<PE, BLOB_COL_LOG, BLOB_ROW_LOG>; COSET_N]
);
```

其中，`COSET_N = 3` 表示陪集数量。

### 1.2 分析范围

本文档重点分析为单个陪集生成 AMT 证明的时间复杂度。由于三个陪集的处理过程相互独立且结构相同，单个陪集的复杂度分析具有代表性。

### 1.3 AMT 技术原理

AMT 承诺机制基于多项式承诺方案，其核心思想是将数据向量中的所有元素映射为多项式函数 $f(x)$ 上的离散数据点。具体而言，设 $n = 2^k$ 为 2 的幂次，对于包含 $2^k \times 2^k$ 个数据元素的向量，系统采用 $2^{2k}$ 次单位根作为求值域，构建求值点集合：

$$
\{1, \omega, \omega^2, \ldots, \omega^{2^{2k}-1}\}
$$

其中 $\omega$ 为 $2^{2k}$ 次本原单位根，向量元素依次对应为各求值点处的函数值。

#### 1.3.1 可信设置阶段

在系统初始化的可信设置（Trusted Setup）阶段，执行以下步骤：

1. 选取随机秘密值 $\tau \in \mathbb{F}_p$；
2. 计算结构化参考串（Structured Reference String, SRS）：$[\tau^0 G, \tau^1 G, \tau^2 G, \ldots, \tau^{n^2-1} G]$，其中 $G$ 为椭圆曲线生成元；
3. 公开发布 SRS 后，永久性销毁秘密值 $\tau$，确保系统安全性。

基于该 SRS，多项式 $f(x)$ 的 KZG 承诺可表示为 $C = f(\tau) \cdot G$。

#### 1.3.2 层次化分解结构

多项式 f(x) 可分解为拉格朗日基多项式的线性组合：

$$f(x) = \sum_i d_i \cdot L_i(x)$$

其中，$L_i(x)$ 为拉格朗日基多项式，满足克罗内克 δ 函数性质：

$$L_i(\omega^j) = \delta_{ij} = \begin{cases}
1, & \text{当 } i = j \\
0, & \text{当 } i \neq j
\end{cases}$$

该性质确保了多项式 $f(x)$ 在求值点 $\omega^i$ 处的取值恰好等于数据元素 $d_i$，即 $f(\omega^i) = d_i$。该分解结构可进一步表示为二叉树形式，其中：

- **叶子节点**：对应各拉格朗日基多项式 Lᵢ(x)；
- **中间节点**：对应子多项式之和；
- **根节点**：对应完整多项式 f(x)。

**示例说明**：以包含 8 个数据元素的向量为例，设数据向量为：

$$
d = [d_0, d_1, d_2, d_3, d_4, d_5, d_6, d_7]
$$

单位根为：

$$
\omega = e^{2\pi i/8}
$$

则：

```
层次化分解树结构（基于模运算的索引分配）：

注：f_d,t(x) 中下标 d 表示深度，t 表示位置索引。

                        f₀,₀(x) = ∑⁷ᵢ₌₀ dᵢLᵢ(x)
                       /                      \
         f₁,₀(x) = ∑ᵢ∈{0,2,4,6} dᵢLᵢ(x)          f₁,₁(x) = ∑ᵢ∈{1,3,5,7} dᵢLᵢ(x)
              /              \                      /              \
         f₂,₀(x)          f₂,₂(x)              f₂,₁(x)          f₂,₃(x)
         {0,4}            {2,6}                {1,5}            {3,7}
          / \              / \                  / \              / \
       d₀L₀ d₄L₄        d₂L₂ d₆L₆            d₁L₁ d₅L₅        d₃L₃ d₇L₇
```

其中：

\begin{aligned}
f_{1,0}(x) &= d_0 L_0(x) + d_2 L_2(x) + d_4 L_4(x) + d_6 L_6(x) &\quad [T_{1,0} = \{0,2,4,6\}: i \equiv 0 \pmod{2}] \\
f_{1,1}(x) &= d_1 L_1(x) + d_3 L_3(x) + d_5 L_5(x) + d_7 L_7(x) &\quad [T_{1,1} = \{1,3,5,7\}: i \equiv 1 \pmod{2}] \\
f_{2,0}(x) &= d_0 L_0(x) + d_4 L_4(x) &\quad [T_{2,0} = \{0,4\}: i \equiv 0 \pmod{4}] \\
f_{2,1}(x) &= d_1 L_1(x) + d_5 L_5(x) &\quad [T_{2,1} = \{1,5\}: i \equiv 1 \pmod{4}] \\
f_{2,2}(x) &= d_2 L_2(x) + d_6 L_6(x) &\quad [T_{2,2} = \{2,6\}: i \equiv 2 \pmod{4}] \\
f_{2,3}(x) &= d_3 L_3(x) + d_7 L_7(x) &\quad [T_{2,3} = \{3,7\}: i \equiv 3 \pmod{4}]
\end{aligned}

该层次化结构使得证明生成具有对数级复杂度优势，每层节点数减半，树的深度为 log₂(n²)。

## 2. AMT 证明时间复杂度分析

为单个陪集生成完整的 AMT 证明包含以下三个核心组成部分：

1. **商多项式证明树（Quotient Polynomial Proof Tree）**：用于生成批量零知识证明；
2. **KZG 承诺树（KZG Commitment Tree）**：用于构建层次化的多项式承诺结构；
3. **低度测试承诺（Low-Degree Test Commitment）**：用于验证多项式次数约束。

### 2.1 商多项式证明树（Quotient Polynomial Proof Tree）

#### 2.1.1 原理

对于二叉树结构中深度为 $d$、位置索引为 $t$ 的任意节点，定义其对应的求值点索引集合为：

$$T_{d,t} := \{i \in [n^2] \mid i \equiv t \pmod{2^d}\}$$

该集合包含所有索引 $i$ 模 $2^d$ 后与 $t$ 同余的求值点。相应地，定义其对应的子多项式为 $f_{d,t}(x)$，该多项式具有如下特性：

1. 在该节点对应的求值点集合 $T_{d,t}$ 上， $f_{d,t}(x)$ 与原多项式 f(x) 的取值保持一致；
2. 在集合 $T_{d,t}$ 的补集 $T^c_{d,t}$ 上， $f_{d,t}(x)$ 的取值恒为 0。

为证明 $f_{d,t}(x)$ 的有效性，需要构造其商多项式 $h_{d,t}(x)$，定义为：

$$h_{d,t}(x) = \frac{f_{d,t}(x)}{Z_{d,t}(x)}$$

其中， $Z_{d,t}(x)$ 为消失多项式（Vanishing Polynomial），定义为：

$$Z_{d,t}(x) = \prod_{i \in T^c_{d,t}} (x - \omega_i)$$

其中 $T^c_{d,t}$ 表示集合 $T_{d,t}$ 的补集，$\omega_i$ 为补集中的单位根元素。

利用拉格朗日基多项式展开，子多项式 $f_{d,t}(x)$ 可表示为：

$$f_{d,t}(x) = \sum_i d_i \cdot L_i(x)$$

其中 dᵢ 为数据元素，Lᵢ(x) 为拉格朗日基多项式。因此，商多项式的 KZG 承诺可改写为：

$$\begin{aligned}
h_{d,t}(\tau) \cdot G &= \frac{\sum_i d_i \cdot L_i(\tau)}{Z_{d,t}(\tau)} \cdot G \\
&= \sum_i d_i \cdot \frac{L_i(\tau)}{Z_{d,t}(\tau)} \cdot G \\
&= \sum_i d_i \cdot Q_{i,d,t}(\tau) \cdot G
\end{aligned}$$

其中， $Q_{i,d,t} = [L_i(\tau) / Z_{d,t}(\tau)] \cdot G$ 定义为**商多项式基底**（Quotient Basis）。

##### 商多项式基底的计算

商多项式基底定义为：

$$Q_{i,d,t}(x) = \frac{L_i(x)}{Z_{d,t}(x)}$$

其中 $i \in T_{d,t}$，$L_i(x)$ 是拉格朗日基多项式，$Z_{d,t}(x)$ 是消失多项式。

**消失多项式 $Z_{d,t}(x)$ 的定义**（根据论文公式 6-7）：

消失多项式定义为（公式 6）：

$$Z_{d,t}(x) = \prod_{i \in [n^2] \setminus T_{d,t}} (x - \omega^i) = \frac{x^{n^2} - 1}{\prod_{i \in T_{d,t}} (x - \omega^i)}$$

其中分母可以简化为（公式 7）：

$$\prod_{i \in T_{d,t}} (x - \omega^i) = x^{n^2/2^d} - \omega^{t \cdot n^2/2^d}$$

因此，消失多项式的最终表示为：

$$Z_{d,t}(x) = \frac{x^{n^2} - 1}{x^{n^2/2^d} - \omega^{t \cdot n^2/2^d}}$$

**Encoder 中的实际计算方法**：

在 AMT 证明系统中，商多项式基底和消失多项式承诺在证明生成和验证中承担**不同的角色**：

1. **证明生成阶段（Prover）**：
   - 目标：计算商多项式的 KZG 承诺 $h_{d,t}(\tau) \cdot G$
   - 计算方式：$h_{d,t}(\tau) \cdot G = \text{MSM}(\{Q_{i,d,t}(\tau) \cdot G\}, \{d_i\})$
   - 这里 **只需要商多项式基底** $\{Q_{i,d,t}(\tau) \cdot G\}$，不需要消失多项式

2. **验证阶段（Verifier）**：
   - 目标：验证商多项式关系 $C_{d,t}(\tau) = h_{d,t}(\tau) \cdot Z_{d,t}(\tau)$
   - 验证方式：配对检查 $e(C_{d,t}, G_2) = e(h_{d,t}, Z_{d,t}(\tau) \cdot G_2)$
   - 这里 **需要消失多项式承诺** $Z_{d,t}(\tau) \cdot G_2$ 来验证商多项式的正确性

**预计算过程**：

在系统初始化阶段，encoder 使用基于 FFT 的优化算法预计算以下参数：

1. **拉格朗日基底**：通过 IFFT 变换 SRS 得到
   $$\{B_i\} = \text{IFFT}(\{[\tau^0 G, \tau^1 G, \ldots, \tau^{n^2-1} G]\})$$
   其中 $B_i = L_i(\tau) \cdot G$

2. **商多项式基底**：通过优化的 FFT 算法直接计算
   
   对于每个深度 $d \in [1, \log_2 n^2]$，计算：
   $$\{Q_{i,d,t}(\tau) \cdot G\}_{i=0}^{n^2-1}$$
   
   **数学推导**：
   
   根据商多项式的定义 $Q_{i,d,t}(x) = \frac{L_i(x)}{Z_{d,t}(x)}$，我们需要在 $\tau$ 点求值。设 $m = n^2/2^d$。
   
   **拉格朗日基多项式 $L_i(x)$ 的封闭形式**：
   
   拉格朗日基多项式定义为在 $n^2$ 个单位根上满足 $L_i(\omega^j) = \delta_{ij}$ 的唯一多项式：
   
   $$L_i(x) = \prod_{j \neq i} \frac{x - \omega^j}{\omega^i - \omega^j}$$
   
   利用单位根的性质，分子可以化简为：
   $$\prod_{j \neq i} (x - \omega^j) = \frac{x^{n^2} - 1}{x - \omega^i}$$
   
   分母可以通过提取公因子并利用等比多项式恒等式化简：
   $$\prod_{j \neq i} (\omega^i - \omega^j) = \prod_{j \neq i} \omega^i \cdot (1 - \omega^{j-i}) = \omega^{i(n^2-1)} \cdot \prod_{k=1}^{n^2-1} (1 - \omega^k) = \omega^{-i} \cdot \prod_{k=1}^{n^2-1} (1 - \omega^k)$$
   
   其中 $\prod_{k=1}^{n^2-1} (1 - \omega^k)$ 可通过多项式因式分解 $\frac{x^{n^2} - 1}{x - 1} = \sum_{j=0}^{n^2-1} x^j$ 在 $x = 1$ 处求值得到：
   $$\prod_{k=1}^{n^2-1} (1 - \omega^k) = n^2$$
   
   因此：$\prod_{j \neq i} (\omega^i - \omega^j) = n^2 \omega^{-i}$
   
   因此，拉格朗日基多项式的封闭形式为：
   $$L_i(x) = \frac{\omega^i (x^{n^2} - 1)}{n^2 (x - \omega^i)}$$
   
   **消失多项式 $Z_{d,t}(x)$ 的推导**：
   
   根据公式 6-7，消失多项式可以表示为：
   $$Z_{d,t}(x) = \frac{x^{n^2} - 1}{x^m - \omega^{tm}}$$
   
   因此商多项式可以改写为：
   $$Q_{i,d,t}(x) = \frac{L_i(x) \cdot (x^m - \omega^{tm})}{x^{n^2} - 1}$$
   
   在 $\tau$ 点求值：
   $$Q_{i,d,t}(\tau) = \frac{L_i(\tau) \cdot (\tau^m - \omega^{tm})}{\tau^{n^2} - 1}$$
   
   **商多项式 $Q_{i,d,t}(x)$ 的简化形式**：
   
   首先，拉格朗日基多项式有如下封闭形式（单位根上的标准结果）：
   
   $$L_i(x) = \frac{\omega^i (x^{n^2} - 1)}{n^2 (x - \omega^i)}$$
   
   将其代入商多项式定义 $Q_{i,d,t}(x) = \frac{L_i(x)}{Z_{d,t}(x)} = \frac{L_i(x) \cdot (x^m - \omega^{tm})}{x^{n^2} - 1}$：
   
   $$Q_{i,d,t}(x) = \frac{\omega^i (x^{n^2} - 1)}{n^2 (x - \omega^i)} \cdot \frac{x^m - \omega^{tm}}{x^{n^2} - 1} = \frac{\omega^i (x^m - \omega^{tm})}{n^2 (x - \omega^i)}$$
   
   这是一个非常简洁的形式！
   
   **验证代码中的计算公式**：
   
   当 $i \in T_{d,t}$（即 $i \equiv t \pmod{2^d}$）时，有 $\omega^{im} = \omega^{tm}$。
   
   利用等比数列求和公式：
   $$\frac{x^m - \alpha^m}{x - \alpha} = \sum_{j=0}^{m-1} x^{m-1-j} \alpha^j = \alpha^{m-1} \sum_{j=0}^{m-1} x^j \alpha^{-j}$$
   
   令 $\alpha = \omega^i$，$\omega^{tm} = \omega^{im}$，代入得：
   
   $$Q_{i,d,t}(x) = \frac{\omega^i}{n^2} \cdot \omega^{i(m-1)} \sum_{j=0}^{m-1} x^j \omega^{-ij} = \frac{\omega^{im}}{n^2} \sum_{j=0}^{m-1} \omega^{-ij} x^j$$
   
   在 $x = \tau$ 处求值并乘以 $G$：
   
   $$Q_{i,d,t}(\tau) \cdot G = \frac{\omega^{im}}{n^2} \sum_{j=0}^{m-1} \omega^{-ij} \cdot [\tau^j G]$$
   
   这正是代码中 `simple_gen_quotinents` 函数计算的结果！
   
   **实际算法**（对应 `gen_quotients` 函数）：
   
   设 $m = n^2/2^d$，$\omega$ 为 $n^2$ 次单位根。根据代码中的 `simple_gen_quotinents` 函数，对于索引 $i$，商多项式基底的计算公式为：
   
   $$Q_i(\tau) \cdot G = \frac{\omega^i}{n^2} \cdot \sum_{j=0}^{m-1} \omega^{ij} \cdot [\tau^{m-j} G]$$
   
   或等价地写为：
   
   $$Q_i(\tau) \cdot G = \frac{\omega^i}{n^2} \cdot \sum_{k=0}^{m-1} \omega^{i(m-k)} \cdot [\tau^k G]$$
   
   **详细推导**：
   
   1. **从单位根上的值出发**
      
      我们已经知道 $Q_i(\omega^k) = \frac{\omega^{ik} \cdot (\omega^{km} - \omega^{tm})}{n^2}$
      
      对于特定的深度 $d$ 和位置 $t$，消失多项式是固定的，商多项式 $Q_i(x)$ 在所有 $n^2$ 个单位根 $\{\omega^0, \omega^1, \ldots, \omega^{n^2-1}\}$ 上的值已知。
   
   2. **多项式由单位根上的值决定**
      
      一个次数 $< n^2$ 的多项式可以由它在 $n^2$ 个不同点上的值唯一确定。我们可以将 $Q_i(x)$ 表示为：
      $$Q_i(x) = \sum_{k=0}^{n^2-1} Q_i(\omega^k) \cdot L_k(x)$$
      
      其中 $L_k(x)$ 是基于单位根 $\omega^k$ 的拉格朗日基多项式。
   
   3. **在 $\tau$ 点求值**
      
      将 $x = \tau$ 代入并两边乘以 $G$：
      $$Q_i(\tau) \cdot G = \sum_{k=0}^{n^2-1} Q_i(\omega^k) \cdot [L_k(\tau) \cdot G]$$
      
      注意到 $L_k(\tau) \cdot G$ 就是拉格朗日基底 $B_k$。
   
   4. **利用单位根上的特殊结构**
      
      对于特定的 $(d, t)$，消失多项式在补集 $T_{d,t}$ 上为零。这意味着很多 $Q_i(\omega^k)$ 项会包含 $(\omega^{km} - \omega^{tm})$ 这个因子，这使得求和可以简化。
      
      经过代数化简和重排，最终可以将求和表示为只涉及 SRS 中前 $m$ 个元素的形式：
      $$Q_i(\tau) \cdot G = \frac{\omega^i}{n^2} \cdot \sum_{j=0}^{m-1} \omega^{ij} \cdot [\tau^{m-j} G]$$
      
   5. **公式的物理意义**
      
      这个公式说明：
      - 只需要 SRS 中的前 $m = n^2/2^d$ 个元素 $[\tau^0 G, \tau^1 G, \ldots, \tau^{m-1} G]$
      - 通过单位根 $\omega$ 的幂次进行加权求和
      - 最后乘以 $\frac{\omega^i}{n^2}$ 进行归一化
      
      这正是 FFT 擅长计算的形式！
   
   6. **等价形式**
      
      通过变量替换 $k = m - j$，可以将公式改写为：
      $$Q_i(\tau) \cdot G = \frac{\omega^i}{n^2} \cdot \sum_{k=0}^{m-1} \omega^{i(m-k)} \cdot [\tau^k G]$$
      
      这两种形式是等价的，只是求和的顺序不同。
   
   这个公式可以通过以下步骤高效计算：
   
   a. **构造系数向量**：
      $$\text{coeff}[j] = \begin{cases}
      0 & j = 0 \\
      [\tau^{m-j} G] & 1 \leq j \leq m \\
      0 & m < j < n^2
      \end{cases}$$
   
   b. **执行 FFT**：
      $$\text{temp}[i] = \text{FFT}(\text{coeff})[i] = \sum_{j=0}^{n^2-1} \text{coeff}[j] \cdot \omega^{ij}$$
      
      由于 $\text{coeff}[j] = 0$ 当 $j > m$ 或 $j = 0$，实际上：
      $$\text{temp}[i] = \sum_{j=1}^{m} [\tau^{m-j} G] \cdot \omega^{ij} = \sum_{k=0}^{m-1} [\tau^k G] \cdot \omega^{i(m-k)}$$
      
      这正是：
      $$\text{temp}[i] = \omega^{im} \cdot \sum_{k=0}^{m-1} \omega^{-ik} \cdot [\tau^k G]$$
   
   c. **归一化**：
      $$Q_i(\tau) \cdot G = \frac{\text{temp}[i]}{n^2}$$
   
   这个算法的妙处在于：
   - 通过精心构造系数向量，使得 FFT 直接计算出所需的求和
   - 避免了显式计算 $L_i(\tau)$ 和 $Z_{d,t}(\tau)$，然后再做除法
   - 时间复杂度从 $O(n^2)$ 的直接计算降为 $O(n^2 \log n)$ 的 FFT

3. **消失多项式承诺**：计算 $Z_{d,t}(\tau) \cdot G_2$ 在 $G_2$ 群上
   
   对于每个深度 $d$ 和节点位置 $t$，计算：
   $$\{Z_{d,t}(\tau) \cdot G_2\}$$
   
   具体实现中，设 $\text{step} = n^2/2^d$，通过以下方式计算：
   - 构造系数向量并对 SRS 的 $G_2$ 部分执行特殊的 FFT 变换
   - 得到所有位置的消失多项式承诺

**正确性验证**：

Encoder 的实现保证了以下配对等式成立：

$$e(B_i, G_2) = e(Q_{i,d,t}(\tau) \cdot G, Z_{d,t}(\tau) \cdot G_2)$$

这验证了数学定义 $L_i(\tau) = Q_{i,d,t}(\tau) \cdot Z_{d,t}(\tau)$ 的正确性。

**为什么同时需要 Q 和 Z？**

- **Q （商多项式基底）**：
  - 用于 Prover 计算证明：$h_{d,t}(\tau) \cdot G = \sum_i d_i \cdot Q_{i,d,t}(\tau) \cdot G$
  - 存储在 $G_1$ 群上，用于 MSM 计算
  - 存储量：$O(n^2 \log n)$ 个 $G_1$ 点

- **Z （消失多项式承诺）**：
  - 用于 Verifier 验证证明：$e(C_{d,t}, G_2) = e(h_{d,t}, Z_{d,t}(\tau) \cdot G_2)$
  - 存储在 $G_2$ 群上，用于配对验证
  - 存储量：$O(n \log n)$ 个 $G_2$ 点（因为每个深度只有 $2^d$ 个不同的 $Z_{d,t}$）

这两者的分工体现了 KZG 承诺方案的经典设计：Prover 使用 $G_1$ 群进行高效的 MSM 计算，Verifier 使用 $G_2$ 群进行简洁的配对验证。

**预计算与存储**：

由于商多项式基底仅依赖于树结构和 SRS，与具体数据无关，因此：
- 在系统初始化时一次性预计算所有 $Q_{i,d,t}(\tau) \cdot G$
- 对于树中每个节点 $(d, t)$ 和每个索引 $i \in T_{d,t}$，存储对应的 $Q_{i,d,t}(\tau) \cdot G$
- 总存储量：$O(n^2 \log n)$ 个椭圆曲线点

**计算商多项式承诺**：

有了预计算的商多项式基底后，对于数据向量 $\{d_i\}$，商多项式承诺可以通过单次 MSM 计算：

$$h_{d,t}(\tau) \cdot G = \sum_{i \in T_{d,t}} d_i \cdot Q_{i,d,t}(\tau) \cdot G$$

时间复杂度：$O(|T_{d,t}|) = O(n^2/2^d)$

#### 2.1.2 计算复杂度分析

##### 树结构参数
- 树的深度：D = log₂(n²) = 2log₂ n；
- 第 d 层的节点数量：Nᵈ = 2ᵈ；
- 第 d 层每个节点包含的数据元素数：Eᵈ = n² / 2ᵈ。

##### 全树计算

对于第 d 层的任意节点，需要计算其商多项式的 KZG 承诺 $h_{d,t}(\tau) \cdot G$ 。商多项式基底 $\{Q_{i,d,t}(\tau) \cdot G\}$ 仅依赖于树结构和可信设置参数，与具体数据无关。因此可在系统初始化阶段进行预计算并存储。对于给定的数据向量 d = [d₀, d₁, ..., d_{E-1}]，商多项式承诺的计算简化为单次 MSM 操作：

$$h_{d,t}(\tau) \cdot G = \text{MSM}(\{Q_{i,d,t}(\tau) \cdot G\}, \{d_i\})$$

计算第 d 层一个节点时间复杂度为 O(Eᵈ) = O(n² / 2ᵈ)。

计算第 d 层的时间复杂度为2ᵈ * (Eᵈ) = O(n²)

总体时间复杂度：

$$\begin{aligned}
T(n) &= \log_2(n^2) \times O(n^2) \\
&= 2\log_2 n \times O(n^2) \\
&= O(n^2 \log n)
\end{aligned}$$


### 2.2 KZG 承诺树（KZG Commitment Tree）

#### 2.2.1 原理

AMT 二叉树结构中的每个节点均具有对应的 KZG 承诺。对于深度为 d、位置索引为 t 的任意节点，其对应的数据集合为 $T_{d,t}$，对应的子多项式为 $f_{d,t}(x)$，KZG 承诺定义为：

$$C_{d,t} = f_{d,t}(\tau) \cdot G$$

利用拉格朗日基多项式进行展开， $f_{d,t}(x)$ 可表示为：

$$f_{d,t}(x) = \sum_i d_i \cdot L_i(x)$$

其中 dᵢ 为数据集合 $T_{d,t}$ 中的元素，Lᵢ(x) 为对应于原始数据中索引位置的拉格朗日基多项式。因此，该节点的 KZG 承诺可改写为：

$$\begin{aligned}
C_{d,t} &= f_{d,t}(\tau) \cdot G \\
&= [\sum_i d_i \cdot L_i(\tau)] \cdot G \\
&= \sum_i d_i \cdot [L_i(\tau) \cdot G] \\
&= \sum_i d_i \cdot B_i
\end{aligned}$$

其中 $B_i = L_i(\tau) \cdot G$ 定义为**拉格朗日基底**（Lagrange Basis）。

##### 预计算优化

拉格朗日基底 $\{B_i\}$ 可通过对结构化参考串（SRS）执行逆快速傅里叶变换（Inverse Fast Fourier Transform, IFFT）在系统初始化阶段预计算获得：

$$\{B_i\} = \text{IFFT}(\{[\tau^0 G, \tau^1 G, \ldots, \tau^{n^2-1} G]\})$$

因此，任意节点的 KZG 承诺可通过单次 MSM 操作高效计算：

$$C_{d,t} = \text{MSM}(\{B_i\}, \{d_i\})$$

#### 2.2.2 计算复杂度分析

KZG 承诺树的构建过程分为两个阶段：

##### 阶段一：叶子层承诺计算

对于包含 n×n 个数据元素的完整数据集，其叶子层结构分析如下：

- **叶子节点数量**：叶子层共有 n 个节点；
- **每个叶子节点包含的元素数**：n 个数据元素；
- **叶子层总元素数**：n × n = n² 个数据元素。

对于单个叶子节点，其 KZG 承诺通过 MSM 操作计算：

$$C_{\text{叶子}} = \text{MSM}(\{B_i\}, \{d_i\})$$

其中 {dᵢ} 为该叶子节点包含的 n 个数据元素，{Bᵢ} 为对应的拉格朗日基底。MSM 操作的时间复杂度与标量数量呈线性关系，因此单个叶子节点的计算复杂度为：

$$T_{\text{单叶子}} = O(n)$$

叶子层总体计算复杂度为所有叶子节点计算复杂度之和：

$$\begin{aligned}
T_{\text{叶子层}}(n) &= n \times T_{\text{单叶子}} \\
&= n \times O(n) \\
&= O(n^2)
\end{aligned}$$

##### 阶段二：树结构聚合

从叶子层向上递归构建二叉树，父节点的 KZG 承诺通过其两个子节点承诺的椭圆曲线加法计算：

$$C_{\text{父}} = C_{\text{左子}} + C_{\text{右子}}$$

树中总节点数为n。每次椭圆曲线加法的时间复杂度为 O(1)，因此聚合阶段的总体复杂度为：

$$T_{\text{聚合}}(n) = O(n)$$

##### 总体复杂度

综合两个阶段的复杂度：

$$\begin{aligned}
T_{\text{总}}(n) &= T_{\text{叶子}}(n) + T_{\text{聚合}}(n) \\
&= O(n^2) + O(n) \\
&= O(n^2)
\end{aligned}$$

### 2.3 低度测试承诺（Low-Degree Test Commitment）

#### 2.3.1 原理

##### 背景：Trusted Setup 与 SRS 范围

Trusted Setup 生成的结构化参考串（SRS）包含：
$$[G, \tau G, \tau^2 G, \ldots, \tau^{2^{28}-1} G]$$

其中 $2^{28}$ 的来源是：$\tau \in \mathbb{F}_p$，且 $2^{28} | (p-1)$ 但 $2^{29} \nmid (p-1)$。

##### Low Degree Test 的目标

设数据规模是$n^2$, $n = 2^k$, 对于数据编码，算法要求多项式 $P(x)$ 的次数 $< 2^{2k}$。这意味着多项式承诺应该只是以下 SRS 元素的线性组合：
$$[G, \tau G, \tau^2 G, \ldots, \tau^{2^{2k}-1} G]$$

**Low Degree Test 的核心目标**：验证证明者没有使用超出范围的 SRS 元素：
$$[\tau^{2^{2k}} G, \tau^{2^{2k}+1} G, \ldots, \tau^{2^{28}-1} G]$$

如果攻击者使用了这些高次项，他们可以构造次数 $\geq 2^{2k}$ 的多项式，破坏冗余编码的数据可恢复性。

##### 低度测试承诺的定义

对于次数 $< 2^{2k}$ 的多项式 $P(x)$，其低度测试承诺（又称高度承诺，High Commitment）定义为：

$$H = \tau^{2^{28} - 2^{2k}} \cdot P(\tau) \cdot G$$

这个定义的关键洞察：如果 $P(x)$ 的次数确实 $< 2^{2k}$，那么 $\tau^{2^{28} - 2^{2k}} \cdot P(\tau)$ 的最高次项为：
$$\tau^{2^{28} - 2^{2k} + (2^{2k} - 1)} = \tau^{2^{28} - 1}$$

这恰好在 SRS 的有效范围内！

##### 高度基底（High Basis）

为高效计算低度测试承诺，系统预计算高度基底，其构造过程如下：

1. 从 SRS 中提取高阶子集： $[\tau^{2^{28}-2^{2k}} G, \tau^{2^{28}-2^{2k}+1} G, \ldots, \tau^{2^{28}-1} G]$ ；
2. 对该子集执行 IFFT 变换，获得高度拉格朗日基底：

$$\begin{aligned}
\{H\_{Bi}\} &= \text{IFFT}(\{[\tau^{2^{28}-2^{2k}} G, \tau^{2^{28}-2^{2k}+1} G, \ldots, \tau^{2^{28}-1} G]\}) \\
&= \tau^{2^{28}-2^{2k}} \cdot \text{IFFT}(\{[G, \tau G, \ldots, \tau^{2^{2k}-1} G]\}) \\
&= \tau^{2^{28}-2^{2k}} \cdot \{[L_0(\tau) G, L_1(\tau) G, \ldots, L_{2^{2k}-1}(\tau) G]\}
\end{aligned}$$

利用高度基底，低度测试承诺可通过单次 MSM 操作计算：

$$\begin{aligned}
H &= \text{MSM}(\{H\_{Bi}\}, \{d_i\}) \\
&= \sum_i d_i \cdot H\_{Bi} \\
&= \tau^{2^{28}-2^{2k}} \cdot \sum_i d_i \cdot L_i(\tau) \cdot G \\
&= \tau^{2^{28}-2^{2k}} \cdot P(\tau) \cdot G
\end{aligned}$$

##### 验证机制

低度测试承诺的验证通过双线性配对完成。验证者检查以下配对等式是否成立：

$$e(H, G_2) = e(C, \tau^{2^{28}-2^{2k}} \cdot G_2)$$

其中 $C = P(\tau) \cdot G$ 为标准 KZG 承诺。等式成立的数学验证：

$$\begin{aligned}
e(H, G_2) &= e(\tau^{2^{28}-2^{2k}} \cdot P(\tau) \cdot G, G_2) \\
&= e(P(\tau) \cdot G, \tau^{2^{28}-2^{2k}} \cdot G_2) \\
&= e(C, \tau^{2^{28}-2^{2k}} \cdot G_2)
\end{aligned}$$

SRS 的 $G_2$ 组元素 $[\tau^{2^{28}-2^{2k}} G_2, G_2]$ 均为预计算值，验证过程仅需执行两次配对运算，计算开销为常数级。

##### 安全机制

低度测试承诺的核心安全目标是防止 Disperser 提交次数 $\geq 2^{2k}$ 的高次多项式作为数据编码。如果攻击者使用高次多项式 $P'(x)$（次数 $\geq 2^{2k}$）进行伪造，将导致数据可恢复性损失——高次多项式在单位根上的求值可能与原始 $2^{2k}-1$ 次多项式一致，但在原始数据部分丢失的情况下，无法通过冗余数据恢复出正确的 $2^{2k}-1$ 次多项式，破坏了冗余编码的核心安全保证。

##### SRS 约束机制

攻击者试图伪造低度测试承诺 $H'$ 时，需要计算：

$$H' = \tau^{2^{28}-2^{2k}} \cdot P'(\tau) \cdot G$$

对于次数为 $\deg(P') \geq 2^{2k}$ 的高次多项式，其最高次项系数对应的 SRS 元素为：

$$\tau^{2^{28}-2^{2k} + \deg(P')} \cdot G, \quad \text{其中} \quad 2^{28}-2^{2k} + \deg(P') \geq 2^{28}-2^{2k} + 2^{2k} = 2^{28}$$

然而，SRS 的有效范围仅为 $[\tau^0 G, \tau^1 G, \ldots, \tau^{2^{28}-1} G]$，**不包含次数 $\geq 2^{28}$ 的元素**。因此，攻击者无法获取所需的 SRS 元素，无法计算出正确的 $H'$。

##### 基底表达能力限制

即使使用拉格朗日基底进行 MSM 计算，预计算的高度基底 $H_{Bi}$ 仅能表示次数 $< 2^{2k}$ 的多项式。对于高次多项式，其系数向量在拉格朗日基下的表示不在预计算空间内。

##### 安全结论

综上所述，攻击者可能伪造标准 KZG 承诺 $C'$，但无法计算出与之对应的有效低度测试承诺 $H'$，因此无法通过配对验证。这确保了系统只接受次数 $< 2^{2k}$ 的多项式编码数据。

#### 2.3.2 计算复杂度分析

低度测试承诺的计算通过单次 MSM 操作完成：

$$H = \text{MSM}(\{H\_{Bi}\}, \{d_i\})$$

其中 $H_{Bi}$ 为预计算的高度基底（包含 $2^{2k} = n^2$ 个元素），$d_i$ 为数据向量（包含 $n^2$ 个元素）。MSM 操作的时间复杂度为：

$$T_{\text{低度测试}}(n) = O(n^2)$$

### 总结
| 组成部分 | 时间复杂度 |
|---------|-----------|
| 商多项式证明树（Quotient Polynomial Proof Tree） | $O(n^2 \log n)$ |
| KZG 承诺树（KZG Commitment Tree） | $O(n^2)$ |
| 低度测试承诺（Low-Degree Test Commitment） | $O(n^2)$ |

总体时间复杂度为 $O(n^2 \log n)$

