DA Encoding & Recovery 算法原理与代码映射文档
本文档旨在阐述 DA（Data Availability）模块中数据编码（Encoding）与恢复（Recovery）的核心算法原理，并建立算法逻辑与代码实现的对应关系。

1. 核心概念与数学定义
在深入代码之前，首先定义数据与多项式之间的映射关系。

1.1 数据多项式 $f(x)$
假设原始数据块 raw_blob 是一个 BLOB_ROW_N 行 BLOB_COL_N 列的矩阵，BLOB_ROW_N * BLOB_COL_N 记为 $2^d$。我们构造一个多项式 $f(x)$，其次数不超过 $2^d - 1$。

映射规则：将 raw_blob 转置后，视为多项式在单位根上的 Evaluations。
公式： $$ \text{Transposed(raw_blob)} = [f(w^0), f(w^1), \dots, f(w^{2^d-1})] $$ 其中 $w$ 是 $2^d$ 次单位根（$w^{2^d}=1$）。
1.2 扩展与 Cosets
为了实现纠删码（Erasure Coding），我们将数据扩展到多个不相交的陪集（Cosets）上。

Coset 0: $f(1 \cdot \omega^k)$ （原始数据），偏移量 $g_0 = 1$。
Coset $i$: $f(g_i \cdot \omega^k)$，其中偏移量 $g_i$ 由 coset_factor(i) 计算得出。
注：$g_i$ 是基于位反转（Bit-Reversal）逻辑生成的生成元幂次，用于确保所有陪集在几何上互不相交。
扩展后的数据是原数据的 COSET_N 倍，代码编译时保证 COSET_N 最大为 3。

2. 编码流程 (process_blob 函数)
函数 amt::blob::encode::EncoderParams::process_blob 的目的是将原始数据通过 RS 编码扩展，并为每个 Coset 生成 AMT 承诺（Commitment）和证明（Proofs），从而实现既能纠删恢复数据，又能快速验证任意行的数据可用性。

关键步骤解析
矩阵转置与展平 (change_matrix_direction)

操作：将行优先展平的 raw_blob 进行二维转置，结果仍以行优先顺序存为 points。
逻辑：原数据的 $i$ 行 $j$ 列 $\rightarrow$ points 的 $j$ 行 $i$ 列。
索引：points[BLOB_ROW_N * j + i] 存储的是原数据 $i$ 行 $j$ 列的值。这对应了 $f(x)$ 定义中的转置关系。
生成 Coset 数据 (to_coset_blob)

输入：points（即多项式在 $w^k$ 上的值）。
操作：通过 FFT/IFFT 计算 $f(x)$ 在不同 Coset 偏移量下的 Evaluations。
输出：对应 Coset 的数据向量。
构建 HalfBlob (half_blob::generate)

位反转 (Bit-reversal)：对 Coset 数据进行位反转排列。
目的：points[BLOB_ROW_N * j + i] 存储的是原数据 $i$ 行 $j$ 列的值, 位反转后，索引由 $i$（原行号）决定高位，$j$（原列号）决定低位。这意味着原数据的每行在 AMT 里都在一块儿。
生成证明 (gen_amt_proofs)：基于位反转后的数据生成 AMT commitment 和 proofs。
还原顺序：生成证明后，将数据 Bit-reverse 回来，并再次 change_matrix_direction，使其行列结构与原数据一致。
输出

返回 [HalfBlob; COSET_N]，其中包含了与原数据行列对应的扩展数据、承诺及可以很快获得原数据的行的证明。
3. 数据恢复算法 (data_poly 函数)
当部分数据丢失时，我们需要从剩余数据中恢复出原始的 raw_blob。

3.1 问题定义
全集 $A$：所有可能的数据位置，大小为 COSET_MORE * BLOB_ROW_N * BLOB_COL_N。包含：
原始数据位置。
RS 扩展出的数据位置。
"想象出来"的填充位置（COSET_MORE 是 COSET_N.next_power_of_two()，用于补齐 $2$ 的幂次，实际上不存在数据，视为丢失）。
丢失集 $S$：数据丢失的位置集合（包括上述"想象出来"的位置）。
目标：恢复多项式 $f(x)$，其在全集 $A$ 上的 Evaluations 即为完整数据。
特点：数据总是整行整行丢失。
条件：|A| - |S| >= BLOB_ROW_N * BLOB_COL_N。
3.2 核心多项式定义
$p(x)$ (Erased Data Poly)：

在数据存在的点：$p(x) = f(x)$。
在数据丢失的点（$S$）：$p(x) = 0$。
代码对应：$p(x)$ 在全集 $A$ 上的 Evaluations 是代码里的 erasured_data。
$z(x)$ (Zero Poly)：

在数据丢失的点（$S$）：$z(x) = 0$。
是满足该性质的次数最小的多项式。
代码对应：zpoly 函数生成的 zcoeffs。
关系推导： 构造多项式 $(z \cdot p)(x)$。

在未丢失点：$p(x) = f(x) \Rightarrow z(x)p(x) = z(x)f(x)$。
在丢失点：$z(x) = 0 \Rightarrow z(x)p(x) = 0 = z(x)f(x)$。
结论：$(z \cdot p)(x)$ 与 $(z \cdot f)(x)$ 在 $A$ 上的 Evaluations 完全相等。
3.3 恢复步骤详解
第一步：获取 $(z \cdot f)(x)$ 的系数
计算 $z(x)$ 在全集 $A$ 上的 Evaluations (zevals)。
计算 $p(x)$ 在全集 $A$ 上的 Evaluations (erasured_data)。
逐点相乘：data_times_z = zevals * erasured_data。这等价于 $(z \cdot f)(x)$ 在 $A$ 上的 Evaluations。
IFFT：对 data_times_z 做 IFFT。
原理：已知 $deg(f(x)) <= 2^d - 1 < 2^d$, 又已知 $deg(z(x)) = |S|$，而恢复条件是 $|A| - |S| >= 2^d$, 因此，$\deg((z \cdot f)(x)) < 2^d + |S| <= |A|$，因此 IFFT 可以正确还原出 $(z \cdot f)(x)$ 的系数表示 data_times_zcoeffs。
第二步：获取 $z(x)$ 的系数
计算零多项式 $z(x) = \prod_{root \in S} (x - root)$ 是恢复算法中的计算密集型步骤。由于在 DA 场景中，数据丢失通常呈现整行丢失的特性，我们利用这一结构特征额外加速了 $z(x)$ 的构建。

单行丢失的数学特性
假设第 coset_idx 个 Coset 的第 local_idx 行丢失。该行包含 BLOB_COL_N 个数据点。 这些点对应的 Evaluations 位置集合为： $$ { g_{coset_idx} \cdot w^{BLOB_ROW_N \cdot i + local_idx} \mid i = 0, \dots, BLOB_COL_N - 1 } $$ 根据单位根的性质，这 BLOB_COL_N 个根恰好是方程 $$ x^{BLOB_COL_N} = (g_{coset_idx} \cdot w^{local_idx})^{BLOB_COL_N} $$ 的解。记 $$ C_{row} = - (g_{coset_idx} \cdot w^{local_idx})^{BLOB_COL_N}. $$ 该行对应的零多项式为： $$ Z_{row}(x) = x^{BLOB_COL_N} + C_{row} $$ 稀疏性优势：无论 BLOB_COL_N 有多大，该多项式仅有两项非零系数（最高次项系数为 1，常数项为 $C_{row}$）。

构造策略与代码映射
代码通过分治与混合乘法策略来利用这种稀疏性：

预计算 (ZBlob::init)：
系统预先计算所有可能行的常数项 $C_{row}$，避免重复计算幂次。
构建行多项式：
对于每一个丢失的行，直接构造上述的稀疏多项式 $Z_{row}(x) =x^{BLOB_COL_N} + C_{row}$。
对于没有丢失的行，这行的位置都不是 root，这一行对 $z(x)$ 的贡献就是 $Z_{row}(x) = 1$.
分治乘法 (polys_multiply)：

将所有的行多项式放入列表 polys。函数 polys_multiply 将列表 polys 中的所有行多项式相乘。为了优化性能，我们采用构建二叉树、自底向上两两相乘的分治策略，并结合多项式的稀疏特性实现了智能混合乘法。

多项式的稀疏结构分析：

初始状态：
若某一行未丢失，其对应的多项式为 $1$（即 Poly::One()）。
若某一行丢失，其初始多项式仅包含两个非零系数：$c_{\text{BLOB_COL_N}} = 1$ 以及常数项 $c_{0} = C_{row}$。
合并后的结构：
包含 $e$ 行丢失数据的多项式，其次数为 $\text{BLOB_COL_N} \times e$。
关键特性：该多项式仅在下标为 $\text{BLOB_COL_N}$ 的整数倍处可能存在非零系数。因此，非零系数的个数至多为 $e + 1$ 个。
混合乘法策略 (multiply 接口，获得乘积多项式的系数表示)： 当合并两个分别包含 $e_1$ 行和 $e_2$ 行丢失数据的多项式时，结果多项式的次数为 $\text{BLOB_COL_N} \times (e_1 + e_2)$，且依然保持上述稀疏特性。底层接口会根据计算量对比，自动选择最优算法：

稀疏乘法 (multiply_sparse)：利用 Hashmap 存储稀疏系数直接相乘。复杂度为 $O(e_1 \times e_2)$。关键点在于：这里的复杂度仅依赖于丢失的行数，完全不受列宽 $\text{BLOB_COL_N}$ 的影响。
稠密乘法 (multiply_dense)：FFT 域乘法（系数到 Evaluations，Evaluations 相乘，Evaluations 到系数）。复杂度为 $O(N \log N)$，其中 $N = \text{BLOB_COL_N} \times (e_1 + e_2)$。关键点在于：这里的复杂度依赖于丢失的位置总数（即多项式的次数），相比稀疏乘法，它引入了 $\text{BLOB_COL_N}$ 这一倍数因子。
策略优势：这并非传统的 $n^2$ 与 $n \log n$ 的简单对比。在生产环境中，$\text{BLOB_COL_N}$ 通常较大（例如 $2^{10}$）。由于稀疏乘法巧妙地规避了这一倍数因子，即使在 $e_1, e_2$ 稍大的情况下，其计算量仍可能小于包含 $2^{10}$ 因子的 FFT 运算。因此，稀疏乘法在整个分治过程中具有显著的性能优势。
分治流程与复杂度分析： 算法将 polys 中的每个多项式视为叶子节点，构造二叉树，兄弟节点对应的多项式两两相乘生成父节点，直至树根。整个过程调用的乘法次数与规模如下：

第 1 层：$\frac{\text{COSET_MORE} \times \text{BLOB_ROW_N}}{2}$ 次乘法，规模 $e_1, e_2 \le 1$。
第 2 层：$\frac{\text{COSET_MORE} \times \text{BLOB_ROW_N}}{4}$ 次乘法，规模 $e_1, e_2 \le 2$。
...
顶层：1 次乘法，规模 $e_1, e_2 \le \frac{\text{COSET_MORE} \times \text{BLOB_ROW_N}}{2}$。
综合各层计算，polys_multiply(polys) 的总时间复杂度为： $$ O\left( N\cdot \log N \cdot \log(\text{COSET_MORE} \cdot \text{BLOB_ROW_N})\right) $$ 其中，$N = \text{COSET_MORE} \cdot \text{BLOB_ROW_N} \cdot \text{BLOB_COL_N}$。

注意：上述公式是按照全部采用稠密乘法计算得出的理论上限。在实际运行中，由于底层接口可以智能选择稀疏乘法（特别是在树的底层和中层），规避了大量的 FFT 开销，因此实际性能会显著优于该理论上限。

第三步：多项式除法 $f(x) = \frac{(z \cdot f)(x)}{z(x)}$
直接在 Evaluation 域做除法行不通，因为 $z(x)$ 在很多点上是 $0$。我们采用 随机 $k$ 缩放法 来规避除零错误。

算法流程（对应 data_poly 中的 for 循环）：

随机选择 $k$。
构造 $(z \cdot f)(kx)$：
利用系数性质：若 $A(x) = \sum c_i x^i$，则 $A(kx) = \sum (c_i k^i) x^i$。通过第一步获得的 $(z \cdot f)(x)$ 的系数，计算 $(z \cdot f)(kx)$ 的系数，即代码里的 data_times_zcoeffs_kx。
再通过 FFT：得到 $(z \cdot f)(kx)$ 在全集 $A$ 上的 Evaluations，即代码里的 data_times_z_kx_evals。
构造 $z(kx)$：
同理，利用系数缩放，通过第二步获得的 $z(x)$ 的系数，得到 $z(kx)$ 的系数，即代码里的 zcoeffs_kx。
再通过 FFT：得到 $z(kx)$ 在全集 $A$ 上的 Evaluations，即代码里的 z_kx_evals。
逐点相除：
尝试计算 $f(kx)$ 在全集 $A$ 上的 Evaluations，即代码里的 data_kx_evals。
关键：由于 $k$ 是随机选择的，$z(kx)$ 的根（即 $S$ 中的点除以 $k$）大概率不会落在全集 $A$ 的位置点上，从而避免除零。
代码中使用 inverse_vec_checked 进行批量求逆（$O(n)$），若失败则更换 $k$。
还原 $f(x)$：
IFFT：对上一步获得的 $f(kx)$ 在全集 $A$ 上的 Evaluations 进行 IFFT，得到 $f(kx)$ 的系数 data_kx_coeffs。
反向缩放：将系数乘以 $k^{-i}$，得到 $f(x)$ 的系数 data_coeffs。
最终恢复：
FFT：将 data_coeffs 转换回 Evaluations，即恢复后的完整数据。
4. 总结
该系统通过以下机制保证了数据的高效可用性验证与恢复：

编码端：利用 RS 码结合行列变换与位反转，生成支持快速行验证（AMT Proofs）的数据结构。
恢复端：
利用 $f(x) = (z \cdot f)(x) / z(x)$ 的关系将插值问题转化为多项式乘除法。
利用 随机 $k$ 缩放法 技巧巧妙解决了除零问题。
利用 行结构稀疏性 极大地加速了零多项式 $z(x)$ 的构造。
参考文献说明： 本文恢复端所采用的通用算法核心（即利用 FFT 在 $O(n \log^2 n)$ 时间内通过零多项式乘法与随机 $k$ 缩放消除除零异常）参考自 Ethereum Research 论坛文章 Reed-Solomon erasure code recovery in n*log^2(n) time with FFTs。该文献主要阐述了基于频域的通用数据恢复数学原理，不涉及本文提及的 AMT Proofs 验证结构或特定的行结构稀疏性优化。