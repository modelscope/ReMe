# MemLens-256K 评测说明

本文对应[多模态记忆文章](./blog_20261009.md#memlens-256k-results)中的两张 LLM-Judge 图，固定报告 2026-10-16 的主实验结果。它说明比较条件和统计依据，不把后续 runner 改进或独立复现结果替换进主图。

## 结果与统计范围 {#results}

使用 MemLens 官方 `agent_subset_195.json` 中的 195 个问题及各自完整的 256K 历史，统一排除下文列出的六个 QID。十行结果均覆盖相同的 189 个问题。LLM-Judge 按官方类别／子类别协议给出逐题 0/1 分；下表为 `100 × 正确数 / 189`，显示到小数点后两位。

| 模型 | 方法 | Judge 正确数 / 189 | LLM-Judge (%) |
| --- | --- | ---: | ---: |
| Qwen3.6-35B-A3B | Full Context Image | 89 / 189 | 47.09 |
| Qwen3.6-35B-A3B | ReMe Text | 78 / 189 | 41.27 |
| Qwen3.6-35B-A3B | ReMe Image | 101 / 189 | 53.44 |
| Qwen3.6-35B-A3B | OpenViking | 70 / 189 | 37.04 |
| Qwen3.6-35B-A3B | Mem0 | 73 / 189 | 38.62 |
| Qwen3.8-Max | Full Context Image | 124 / 189 | 65.61 |
| Qwen3.8-Max | ReMe Text | 100 / 189 | 52.91 |
| Qwen3.8-Max | ReMe Image | 137 / 189 | 72.49 |
| Qwen3.8-Max | OpenViking | 80 / 189 | 42.33 |
| Qwen3.8-Max | Mem0 | 97 / 189 | 51.32 |

ReMe Image 相对 Full Context Image 的提升按未舍入值计算：`100 × (101 − 89) / 189 = 6.35` 个百分点，以及 `100 × (137 − 124) / 189 = 6.88` 个百分点。有效零分和正常空答案保留，不按得分筛题。

## 方法与 Judge 设置 {#evaluation-settings}

| 方法 | 记忆输入与回答阶段的数据访问范围 |
| --- | --- |
| Full Context Image | 回答模型直接读取完整历史文字与原图，不构建或检索记忆。 |
| ReMe Text | 原始文字进入 Auto Memory；回答 Agent 通过 BM25 检索 daily、digest 和原始 session，读取相关文本，不读取图片。 |
| ReMe Image | 原始图文进入 Auto Memory，不注入 Bench 提供的 caption；检索范围与 Text 相同，并通过评测插件的 `read_image` 桥重新读取保存的原图。 |
| OpenViking | 使用原生图片描述和记忆流程；检索限定为 memory，原生默认 top 10，不检索原始 resource/skill。保留 JSON parser 修正，不能称作完全未修改的 upstream。 |
| Mem0 | 使用 Mem0 2.0.4 原生视觉入口摄入原图，同一待测模型、不注入 Bench caption；通过 FAISS/top 20 检索生成的记忆。 |

ReMe 的记忆和回答上下文配置分别为 200,000 / 400,000 tokens，temperature 0、thinking 开启；记忆／压缩与回答输出预算分别为 65,536 / 16,384 tokens。每题使用独立回答 Agent，上限 30 轮，保留原生上下文压缩；Image 的 `read_image` 适配允许读取保存的附件，读取上限 50 MiB、图片保留上限 4,096。参考答案及类别／子类别只用于评分，不提供给候选方法。

Full Context、OpenViking、Mem0 的最终回答模型同样为相应待测模型，temperature 0、thinking 开启、输出预算 16,384 tokens。其记忆阶段不因此采用相同预算：Mem0 保留原生 2,000 tokens、temperature/top_p 0.1；OpenViking 使用原生图片描述流程，另保留图片处理失败显式报错的适配，不把缺图当作成功摄入。

所有行使用 **Qwen3.8-Max** 作为 Judge：temperature **0**、thinking **关闭**、输出预算 **256 tokens**，与候选记忆应用隔离。这里“官方协议”指评分提示词与解析规则，Judge 模型及参数是本次实验配置，并非声称由基准作者统一指定。

因此，图表比较的是这些完整系统设置，不是相同检索范围下单一图片开关的消融实验；也不据此给出成本或速度排名。

## 统一内容审核过滤 {#content-moderation-filter}

对 ReMe、OpenViking、Mem0 在两个模型中的明确服务端内容审核拒绝取 QID 并集，再将同一集合应用于全部方法及两个模型，包括在被排除题上原本成功的方法。过滤不是按得分或笼统 HTTP 状态选择。

下表将明确的审核码简写为 **A** = `InternalError.Algo.DataInspectionFailed`、**B** = `data_inspection_failed`。

| 排除 QID | 支持过滤的直接观测 | 阶段 | 原件中的审核码 |
| --- | --- | --- | --- |
| `q_028cb832` | OpenViking / Max | memory | A + B |
| `q_1d99a36c` | OpenViking / A3B | memory | A + B |
| `q_3b01c02a` | ReMe Text、Image / A3B；OpenViking / A3B、Max；Mem0 / A3B | memory | 前四项：A + B；Mem0：B |
| `q_564a657b` | ReMe Image / Max | answer | A + B |
| `q_600a79aa` | ReMe Image / Max | memory | A + B |
| `q_c9f8e24d` | ReMe Text / Max | answer | A + B |

该清单由十份直接证据支持。memory 拒绝可能属于主实验复用的历史摄入 attempt，而不是后续回答 attempt 的新拒绝。一般 400/429、通用 RuntimeError 或另一个方法的错误不证明当前方法也触发审核。保留原始 195 题及失败证据，报告只统一使用其余 **189/195** 题。

## 独立复现交叉核验 {#independent-reproduction}

独立 ReMe Image 实验使用固定版本 `d3e79918622173306be79ecda6494acadc7c4312`，另在保留原结果的前提下完成一次有界技术恢复。相同过滤后，A3B / Max 覆盖分别为 188/189、187/189；下表每一对只比较完全相同 QID 和 question/reference 的成功结果，不与主图 189 题均值混算。

| 模型 | 配对题数 | 旧 ReMe Image 正确数 | 独立复现正确数 | 旧 → 独立复现 LLM-Judge (%) |
| --- | ---: | ---: | ---: | ---: |
| Qwen3.6-35B-A3B | 188 | 100 | 96 | 53.19 → 51.06 |
| Qwen3.8-Max | 187 | 135 | 134 | 72.19 → 71.66 |

A3B 的 `q_3714b35c`，以及 Max 的 `q_2dcbc8f1`、`q_7c14354d` 仍是未完整摄入的技术缺口，没有计为成功或自动补零。观察到的配对差值为 −2.13 / −0.53 个百分点；没有多次随机重跑或统计等价检验，不将“接近”表述为逐题重现或因果证明。

## 固定配置与来源 {#sources}

- 数据与协议：[MemLens 数据集](https://huggingface.co/datasets/xiyuRenBill/MEMLENS)、[官方评测代码固定版本](https://github.com/xrenaf/MEMLENS/tree/77f3ab9a52fa2d6a17978e2dffe80438a4ecced2)。
- 公开 ReMe 实现：[MemLens runner 与运行说明](https://github.com/wang-qisen/ReMe/blob/f89f166dcf8b5b37a4ed9a5e7c3fdbdd042170d8/benchmark/memlens/README.md)、[候选方法配置](https://github.com/wang-qisen/ReMe/blob/f89f166dcf8b5b37a4ed9a5e7c3fdbdd042170d8/plugins/memlens/src/reme_memlens/benchmark.yaml)、[Judge 配置](https://github.com/wang-qisen/ReMe/blob/f89f166dcf8b5b37a4ed9a5e7c3fdbdd042170d8/plugins/memlens-judge/src/judge_memlens/plugin.yaml)、[Judge 协议](https://github.com/wang-qisen/ReMe/blob/f89f166dcf8b5b37a4ed9a5e7c3fdbdd042170d8/plugins/memlens-judge/src/judge_memlens/protocol.py)。这些目录在该公开提交中与独立实验的 `d3e79918` 相同；不代表五方法主实验全部使用该版本。
- 主实验的 ReMe/OpenViking 外层基线版本为 `a9fa8330e000ca25b7b94a00a64165c0a3a2b8e7`。Full Context 答案原始生成版本为 `16da81cbd7a0594c6e1d080b5c12548ee199fa6c`，随后经 `exp-0007 → exp-1001 → exp-1002` 复用，并非由后续基线版本重新生成。OpenViking 原生补丁版为 `125058ce677e2238eb359ada5b015ee0ff4c4d16`，Mem0 原生版本为 `75a37ec93db7278e3bd9aaf2aa3d6e5139e6789d`。历史适配和环境由实验归档保留，不把当前 main 当作原实验版本。

公开 runner 从新工作区运行 ReMe Image，默认评测原始 195 题；本页六题过滤是结果分析步骤，不是 runner 的隐式数据过滤。数据、依赖（包括 Pillow）和外部模型服务需要单独准备；新的 API 调用不保证逐字复现历史输出。后续依赖、诊断或用量统计修正不追溯改变本页结果。

### 统计来源指纹

本页[结果表](#results)与[过滤清单](#content-moderation-filter)是随文档版本保存的公开统计摘要。数值源冻结于 `20261016T223731.061980`，快照 manifest SHA256 为 `e2133ee23bdf055c6185c09dd62e4f1ab04f4d6e31caea98080915c7d628694c`；逐题统计源 SHA256 为 `10d5f38705562fbd9f2fdaf591dd1e715959fd5ddaac5c16d9650bf8a24f0da5`，十份审核证据的审计清单 SHA256 为 `eff2a737908c0b5e6dc1a8e9dbb52dc4c7120f3f3fd927777f138e9aa69ef538`。

原始问答、图像、日志及完整实验归档未随本文公开。上述指纹用于关联归档，不替代原件，也不构成可离线重放五种方法的完整发布包。
