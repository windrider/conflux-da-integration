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

AMT 承诺机制基于多项式承诺方案，其核心思想是将数据向量中的所有元素映射为多项式函数 f(x) 上的离散数据点。具体而言，设 n = 2ᵏ 为 2 的幂次，对于包含 2ᵏ×2ᵏ 个数据元素的向量，系统采用 2²ᵏ 次单位根作为求值域，构建求值点集合 {1, ω, ω², ..., ω^(2²ᵏ-1)}，其中 ω 为 2²ᵏ 次本原单位根，向量元素依次对应为各求值点处的函数值。

#### 1.3.1 可信设置阶段

在系统初始化的可信设置（Trusted Setup）阶段，执行以下步骤：

1. 选取随机秘密值 $\tau \in \mathbb{F}_p$
2. 计算结构化参考串（Structured Reference String, SRS）：$[\tau^0 G, \tau^1 G, \tau^2 G, \ldots, \tau^{n^2-1} G]$，其中 $G$ 为椭圆曲线生成元
3. 公开发布 SRS 后，永久性销毁秘密值 $\tau$，确保系统安全性

基于该 SRS，多项式 $f(x)$ 的 KZG 承诺可表示为：

$$
C = f(\tau) \cdot G
$$

#### 1.3.2 层次化分解结构

多项式 f(x) 可分解为拉格朗日基多项式的线性组合：

$$
f(x) = \sum_i d_i \cdot L_i(x)
$$

其中，$L_i(x)$ 为拉格朗日基多项式，满足克罗内克 δ 函数性质：

$$
L_i(\omega^j) = \delta_{ij} = \begin{cases}
1, & \text{当 } i = j \\
0, & \text{当 } i \neq j
\end{cases}
$$

该性质确保了多项式 $f(x)$ 在求值点 $\omega^i$ 处的取值恰好等于数据元素 $d_i$，即 $f(\omega^i) = d_i$。该分解结构可进一步表示为二叉树形式，其中：

- **叶子节点**：对应各拉格朗日基多项式 $L_i(x)$
- **中间节点**：对应子多项式之和
- **根节点**：对应完整多项式 f(x)

**示例说明**：以包含 8 个数据元素的向量为例，设数据向量为 d = [d₀, d₁, d₂, d₃, d₄, d₅, d₆, d₇]，单位根为 ω = e^(2πi/8)，则：

```
层次化分解树结构：

                    f(x) = Σᵢ₌₀⁷ dᵢ·Lᵢ(x)
                   /                      \
            f₀(x) = Σᵢ₌₀³ dᵢ·Lᵢ(x)      f₁(x) = Σᵢ₌₄⁷ dᵢ·Lᵢ(x)
              /          \                /          \
    f₀₀(x)=Σᵢ₌₀¹dᵢLᵢ   f₀₁(x)=Σᵢ₌₂³dᵢLᵢ  f₁₀(x)=Σᵢ₌₄⁵dᵢLᵢ  f₁₁(x)=Σᵢ₌₆⁷dᵢLᵢ
      /    \          /    \          /    \          /    \
   d₀L₀  d₁L₁      d₂L₂  d₃L₃      d₄L₄  d₅L₅      d₆L₆  d₇L₇
```

该层次化结构使得证明生成具有对数级复杂度优势，每层节点数减半，树的深度为 $\log_2(n^2)$。

## 2. AMT 证明时间复杂度分析

为单个陪集生成完整的 AMT 证明包含以下三个核心组成部分：

1. **商多项式证明树（Quotient Polynomial Proof Tree）**：用于生成批量零知识证明
2. **KZG 承诺树（KZG Commitment Tree）**：用于构建层次化的多项式承诺结构
3. **低度测试承诺（Low-Degree Test Commitment）**：用于验证多项式次数约束

### 2.1 商多项式证明树（Quotient Polynomial Proof Tree）

#### 2.1.1 原理

对于二叉树结构中深度为 d、位置索引为 t 的任意节点，定义其对应的求值点集合为 $T_{d,t}$，该集合包含该节点负责的所有单位根求值点。相应地，定义其对应的子多项式为 $f_{d,t}(x)$，该多项式具有如下特性：

1. 在该节点对应的求值点集合 $T_{d,t}$ 上，$f_{d,t}(x)$ 与原多项式 f(x) 的取值保持一致
2. 在集合 $T_{d,t}$ 的补集 $T^c_{d,t}$ 上，$f_{d,t}(x)$ 的取值恒为 0

为证明 $f_{d,t}(x)$ 的有效性，需要构造其商多项式 $h_{d,t}(x)$，定义为：

$$
h_{d,t}(x) = \frac{f_{d,t}(x)}{Z_{d,t}(x)}
$$

其中，$Z_{d,t}(x)$ 为消失多项式（Vanishing Polynomial），定义为：

$$
Z_{d,t}(x) = \prod_{i \in T^c_{d,t}} (x - \omega_i)
$$

其中 $T^c_{d,t}$ 表示集合 $T_{d,t}$ 的补集，$\omega_i$ 为补集中的单位根元素。

利用拉格朗日基多项式展开，子多项式 $f_{d,t}(x)$ 可表示为：

$$
f_{d,t}(x) = \sum_i d_i \cdot L_i(x)
$$

其中 $d_i$ 为数据元素，$L_i(x)$ 为拉格朗日基多项式。因此，商多项式的 KZG 承诺可改写为：

$$
\begin{aligned}
h_{d,t}(\tau) \cdot G &= \frac{\sum_i d_i \cdot L_i(\tau)}{Z_{d,t}(\tau)} \cdot G \\
&= \sum_i d_i \cdot \frac{L_i(\tau)}{Z_{d,t}(\tau)} \cdot G \\
&= \sum_i d_i \cdot Q_{i,d,t}(\tau) \cdot G
\end{aligned}
$$

其中，$Q_{i,d,t}(\tau) = L_i(\tau) / Z_{d,t}(\tau)$ 定义为**商多项式基底**（Quotient Basis）的系数形式。

#### 2.1.2 计算复杂度分析

##### 树结构参数

- 树的深度：$D = \log_2(n^2) = 2\log_2 n$
- 第 d 层的节点数量：$N^d = 2^d$
- 第 d 层每个节点包含的数据元素数：$E^d = n^2 / 2^d$

##### 全树计算

对于第 d 层的任意节点，需要计算其商多项式的 KZG 承诺 $h_{d,t}(\tau) \cdot G$。商多项式基底 $\{Q_{i,d,t}(\tau) \cdot G\}$ 仅依赖于树结构和可信设置参数，与具体数据无关。因此可在系统初始化阶段进行预计算并存储。对于给定的数据向量 d = [d₀, d₁, ..., $d_{E-1}$]，商多项式承诺的计算简化为单次 MSM 操作：

$$
h_{d,t}(\tau) \cdot G = \text{MSM}(\{Q_{i,d,t}(\tau) \cdot G\}, \{d_i\})
$$

计算第 d 层一个节点时间复杂度为 $O(E^d) = O(n^2 / 2^d)$。

计算第 d 层的时间复杂度为 $2^d \times E^d = O(n^2)$

总体时间复杂度：

$$
\begin{aligned}
T(n) &= \log_2(n^2) \times O(n^2) \\
&= 2\log_2 n \times O(n^2) \\
&= O(n^2 \log n)
\end{aligned}
$$

### 2.2 KZG 承诺树（KZG Commitment Tree）

#### 2.2.1 原理

AMT 二叉树结构中的每个节点均具有对应的 KZG 承诺。对于深度为 d、位置索引为 t 的任意节点，其对应的数据集合为 $T_{d,t}$，对应的子多项式为 $f_{d,t}(x)$，KZG 承诺定义为：

$$
C_{d,t} = f_{d,t}(\tau) \cdot G
$$

利用拉格朗日基多项式进行展开，$f_{d,t}(x)$ 可表示为：

$$
f_{d,t}(x) = \sum_i d_i \cdot L_i(x)
$$

其中 $d_i$ 为数据集合 $T_{d,t}$ 中的元素，$L_i(x)$ 为对应于原始数据中索引位置的拉格朗日基多项式。因此，该节点的 KZG 承诺可改写为：

$$
\begin{aligned}
C_{d,t} &= f_{d,t}(\tau) \cdot G \\
&= [\sum_i d_i \cdot L_i(\tau)] \cdot G \\
&= \sum_i d_i \cdot [L_i(\tau) \cdot G] \\
&= \sum_i d_i \cdot B_i
\end{aligned}
$$

其中 $B_i = L_i(\tau) \cdot G$ 定义为**拉格朗日基底**（Lagrange Basis）。

##### 预计算优化

拉格朗日基底 $\{B_i\}$ 可通过对结构化参考串（SRS）执行逆快速傅里叶变换（Inverse Fast Fourier Transform, IFFT）在系统初始化阶段预计算获得：

$$
\{B_i\} = \text{IFFT}(\{[\tau^0 G, \tau^1 G, \ldots, \tau^{n^2-1} G]\})
$$

因此，任意节点的 KZG 承诺可通过单次 MSM 操作高效计算：

$$
C_{d,t} = \text{MSM}(\{B_i\}, \{d_i\})
$$

#### 2.2.2 计算复杂度分析

KZG 承诺树的构建过程分为两个阶段：

##### 阶段一：叶子层承诺计算

对于包含 n×n 个数据元素的完整数据集，其叶子层结构分析如下：

- **叶子节点数量**：叶子层共有 n 个节点
- **每个叶子节点包含的元素数**：n 个数据元素
- **叶子层总元素数**：n × n = n² 个数据元素

对于单个叶子节点，其 KZG 承诺通过 MSM 操作计算：

$$
C_{\text{叶子}} = \text{MSM}(\{B_i\}, \{d_i\})
$$

其中 $\{d_i\}$ 为该叶子节点包含的 n 个数据元素，$\{B_i\}$ 为对应的拉格朗日基底。MSM 操作的时间复杂度与标量数量呈线性关系，因此单个叶子节点的计算复杂度为：

$$
T_{\text{单叶子}} = O(n)
$$

叶子层总体计算复杂度为所有叶子节点计算复杂度之和：

$$
\begin{aligned}
T_{\text{叶子层}}(n) &= n \times T_{\text{单叶子}} \\
&= n \times O(n) \\
&= O(n^2)
\end{aligned}
$$

##### 阶段二：树结构聚合

从叶子层向上递归构建二叉树，父节点的 KZG 承诺通过其两个子节点承诺的椭圆曲线加法计算：

$$
C_{\text{父}} = C_{\text{左子}} + C_{\text{右子}}
$$

树中总节点数为 n。每次椭圆曲线加法的时间复杂度为 O(1)，因此聚合阶段的总体复杂度为：

$$
T_{\text{聚合}}(n) = O(n)
$$

##### 总体复杂度

综合两个阶段的复杂度：

$$
\begin{aligned}
T_{\text{总}}(n) &= T_{\text{叶子}}(n) + T_{\text{聚合}}(n) \\
&= O(n^2) + O(n) \\
&= O(n^2)
\end{aligned}
$$

### 2.3 低度测试承诺（Low-Degree Test Commitment）

#### 2.3.1 原理

低度测试承诺（又称高度承诺，High Commitment）是一种用于验证多项式次数约束的密码学机制。对于次数不超过 n²-1 的多项式 P(x)，其低度测试承诺 H 定义为：

$$
H = \tau^{3n^2} \cdot P(\tau) \cdot G
$$

##### 高度基底（High Basis）

为高效计算低度测试承诺，系统预计算高度基底，其构造过程如下：

1. 从 SRS 中提取高阶子集：$[\tau^{3n^2} G, \tau^{3n^2+1} G, \ldots, \tau^{4n^2-1} G]$
2. 对该子集执行 IFFT 变换，获得高度拉格朗日基底：

$$
\begin{aligned}
\{H_{Bi}\} &= \text{IFFT}(\{[\tau^{3n^2} G, \tau^{3n^2+1} G, \ldots, \tau^{4n^2-1} G]\}) \\
&= \tau^{3n^2} \cdot \text{IFFT}(\{[G, \tau G, \ldots, \tau^{n^2-1} G]\}) \\
&= \tau^{3n^2} \cdot \{[L_0(\tau) G, L_1(\tau) G, \ldots, L_{n^{2}-1}(\tau) G]\}
\end{aligned}
$$

利用高度基底，低度测试承诺可通过单次 MSM 操作计算：

$$
\begin{aligned}
H &= \text{MSM}(\{H_{Bi}\}, \{d_i\}) \\
&= \sum_i d_i \cdot H_{Bi} \\
&= \tau^{3n^2} \cdot \sum_i d_i \cdot L_i(\tau) \cdot G \\
&= \tau^{3n^2} \cdot P(\tau) \cdot G
\end{aligned}
$$

##### 验证机制

低度测试承诺的验证通过双线性配对完成。验证者检查以下配对等式是否成立：

$$
e(H, G_2) = e(C, \tau^{3n^2} \cdot G_2)
$$

其中 $C = P(\tau) \cdot G$ 为标准 KZG 承诺。等式成立的数学验证：

$$
\begin{aligned}
e(H, G_2) &= e(\tau^{3n^2} \cdot P(\tau) \cdot G, G_2) \\
&= e(P(\tau) \cdot G, \tau^{3n^2} \cdot G_2) \\
&= e(C, \tau^{3n^2} \cdot G_2)
\end{aligned}
$$

SRS 的 G₂ 组元素 $[\tau^{3n^2}G_2, G_2]$ 均为预计算值，验证过程仅需执行两次配对运算，计算开销为常数级。

##### 安全机制

低度测试承诺的核心安全目标是防止 Disperser 提交次数超过 n²-1 的高次多项式作为数据编码。如果攻击者使用高次多项式 P'(x)（次数 ≥ n²）进行伪造，将数据可恢复行损失，高次多项式在单位根上的求值可能与原始 n²-1 次多项式一致，但在原始数据部分丢失的情况下，无法通过冗余数据恢复出正确的 n²-1 次多项式，破坏了冗余编码的核心安全保证。

##### SRS 约束机制

攻击者试图伪造低度测试承诺 H' 时，需要计算：

$$
H' = \tau^{3n^2} \cdot P'(\tau) \cdot G
$$

对于次数为 $\deg(P') \geq n^2$ 的高次多项式，其最高次项系数对应的 SRS 元素为：

$$
\tau^{3n^2 + \deg(P')} \cdot G, \quad \text{其中} \quad 3n^2 + \deg(P') \geq 3n^2 + n^2 = 4n^2
$$

然而，SRS 的有效范围仅为 $[\tau^0 G, \tau^1 G, \ldots, \tau^{4n^2-1} G]$，不包含次数 ≥ 4n² 的元素。因此，攻击者无法获取所需的 SRS 元素，无法计算出正确的 H'。

##### 基底表达能力限制

即使使用拉格朗日基底进行 MSM 计算，预计算的高度基底 $H_{Bi}$ 仅能表示次数不超过 n²-1 的多项式。对于高次多项式，其系数向量在拉格朗日基下的表示不在预计算空间内。

##### 安全结论

综上所述，攻击者可能伪造标准 KZG 承诺 C'，但无法计算出与之对应的有效低度测试承诺 H'，因此无法通过配对验证。这确保了系统只接受次数不超过 n²-1 的多项式编码数据。

#### 2.3.2 计算复杂度分析

低度测试承诺的计算通过单次 MSM 操作完成：

$$
H = \text{MSM}(\{H_{Bi}\}, \{d_i\})
$$

其中 $H_{Bi}$ 为预计算的高度基底（包含 n² 个元素），$d_i$ 为数据向量（包含 n² 个元素）。MSM 操作的时间复杂度为：

$$
T_{\text{低度测试}}(n) = O(n^2)
$$

## 3. 总结

| 组成部分 | 时间复杂度 |
|---------|-----------|
| 商多项式证明树（Quotient Polynomial Proof Tree） | $O(n^2 \log n)$ |
| KZG 承诺树（KZG Commitment Tree） | $O(n^2)$ |
| 低度测试承诺（Low-Degree Test Commitment） | $O(n^2)$ |

总体时间复杂度为 $O(n^2 \log n)$
