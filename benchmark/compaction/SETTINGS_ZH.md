# 实验设置与复现说明

[English](./SETTINGS.md) | **简体中文**

本文说明[结果页](./RESULTS_ZH.md)中的 **13 组对照**：Full context、通用摘要 S，以及 Hermes 上下文压缩摘要 H；
S、H 分别搭配 Jev Top 0～5。Top 0 表示纯摘要。[实验方案](./STUDY_ZH.md)列出问题、固定答案、评分规则及协议修正。

## 模型与 agent 框架

| 角色 | 实际记录的设置 |
| --- | --- |
| 轨迹采集 | Hermes Agent `AIAgent`，commit `30463589eb54fa0f48724594cc0e98e6b995729b` |
| 采集模型 | `qwen3.8-max`，自定义 OpenAI 兼容 Chat Completions 接口 |
| 通用摘要 S | 直接调用 `qwen3.8-max`，使用 [`cases.py`](./cases.py) 中的任务交接提示词 |
| Hermes 摘要 H | 同样使用 `qwen3.8-max`，调用 Hermes `ContextCompressor._generate_summary`，`tail_mode=legacy` |
| 决策／排名 | Jev，响应中实际解析出的版本为 **`jev-1.13.0`**，经 AgentScope／TypeSafe 调用 |
| 回答 | 直接调用 `qwen3.8-max`，不恢复 agent／工具循环 |
| 评分 | 确定性的递归、类型严格 JSON 字段规则，不使用 LLM judge |
| 实验实现 | ReMe commit `50c2c806446c7ae6acc66217afd6e5edc2114046` |

H 是**小预算设置下的 Hermes 上下文压缩摘要**，复用 Hermes 的序列化、结构化检查点提示词、敏感信息遮蔽和来源校验。
实验覆盖摘要预算并附加总字数上限，再用 Hermes 的辅助函数移除控制前缀。它直接生成摘要，不调用完整的 `compress()`：
自动触发、首尾窗口选择和压缩后的会话修复不在本次比较范围内。因此不能笼统称为整个 Hermes 上下文管理的修改版本。

请求与保存的回答响应仅标识 Qwen 别名，没有提供不可变的服务端权重版本。即使温度为 0，服务端更新和非确定性
仍可能改变新运行的结果。尽量使用同一 `LLM_BASE_URL` 服务；接口及密钥通过私有 `.env` 提供。
本次接口已核实为中国北京地域的公开 DashScope 接口，API Key 不公开。

## 运行环境依赖

使用两个独立 Python 环境。下表版本是**实验结束后从保留环境中核实的版本**，不是运行前固定的锁文件；
可作为复现参考，但不能证明环境已被完整锁定。本地使用 Python **3.13.3**、macOS arm64；推理由外部服务执行，不使用本地 GPU。

| 包 | ReMe 评测环境 | Hermes 采集／摘要环境 |
| --- | --- | --- |
| `openai` | 2.53.0 | 3.31.0 |
| `agentscope` | 2.0.10 | — |
| `typesafe-sdk` | 0.7.5 | — |
| `httpx` | 0.28.1 | 0.28.1 |
| `httpx2` | — | 2.13.1 |
| `python-dotenv` | 1.2.2 | 1.2.4 |
| `pydantic` | 2.13.4 | 2.14.1 |
| `tokenizers` | 0.23.3 | 0.23.3 |

`tokenizers` 来自 `PYTHONPATH` 中的独立包目录，未安装进这两个 venv。新环境可分别安装该精确版本。
本地产物包包含实验结束后记录的两个环境的发行包元数据，不包含凭证或虚拟环境二进制文件。

预算计数使用 `Qwen/Qwen3.5-9B` 的 **`tokenizer.json`**，revision 为
`c202236235762e1c871ad0ccb60c8ee5ba337b9a`，SHA-256 为
`5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42`。
这是**预算估算代理**，不表示 Qwen 3.8 使用该 tokenizer；下游输入的报告值来自 API 的实际 usage。

## 请求参数

| 阶段 | 采样／输出参数 | 执行限制 |
| --- | --- | --- |
| Hermes 采集 | `max_tokens=1024`；`reasoning_effort=none`、`enable_thinking=false`；未显式设置温度或 seed | 最多 12 次 agent 迭代，运行预算 240 秒；4 个 worker；子进程超时 360 秒 |
| S 生成 | `temperature=0`、`max_tokens=4096`；关闭 thinking；无 seed | OpenAI 客户端超时 90 秒，`max_retries=1` |
| H 生成 | `temperature=0`；未显式设置 API `max_tokens`；关闭 thinking；无 seed | 同样为 90 秒客户端超时、1 次 SDK 重试；4 个 worker；子进程超时 600 秒 |
| Jev 排名 | 每个证据块一个二元概率问题，每批 10 块 | 适配器超时 45 秒，`max_retries=2`，重试间隔 0.5 秒 |
| 回答 | `temperature=0`、`max_tokens=2400`、`response_format={"type":"json_object"}`；关闭 thinking；无 seed | 客户端超时 90 秒，`max_retries=1`；4 种条件并发，每种依次回答 2 次 |

直接 Qwen 请求通过 `reasoning_effort="none"` 和 `extra_body={"enable_thinking":false}` 关闭 thinking。
采集阶段的实际网络请求在顶层携带 `enable_thinking=false`。H 的 API 输出限制与摘要正文上限不同：
是否接受摘要由本地正文 token 检查决定。实际运行的请求参数以保存的请求正文为准。

采集仅开放白名单内的 `read_file`，来源工作区只读；关闭自动压缩与 micro compaction，跳过记忆文件、
上下文文件和后台 review。每个 worker 使用独立 `HERMES_HOME`、工作区和会话数据库。
实现见 [`hermes_worker.py`](./hermes_worker.py)。

## 数据、配对与预算

- **14 个任务模板**：1 条复用的合成支付轨迹，以及在上游任务只读改写上实际运行 Hermes 的 13 条轨迹。
  长来源采用确定性的原文开头／匹配行视图，不人为增加噪声。
- 四个主任务为 `payment`、`checkout_504`、`server_error`、`build_token`；另有十个短任务／仅依赖问题的对照。
  分组在采集前按来源长度固定，不依据结果选择。
- 每个任务独立请求 3 轮摘要／排名，每种条件回答 2 次：**14 × 3 × 13 = 546 个上下文，1092 次回答**。
  重复回答不等于独立任务样本。
- S、H 在各自 Top 0～5 中逐字相同，两种机制使用完全一致的 Jev 分数与来源块。
  排名依据原任务，不以摘要为条件。严格按分数降序选择，相同分数按块 ID 排序，再恢复来源顺序。
  不设阈值，不跳过块，也不截断块；实际 N 为 `min(N, available units)`。
- 摘要正文预算为 `max(64, min(256, int(0.2 * evidence_tokens)))`。
  S 最多进行 3 次长度检查尝试，字数目标为 `max(12, int(allowance * 0.4 * 0.8**attempt))`。
- H 最多进行 3 次长度检查尝试。请求预算为 `max(12, int(allowance * 0.8**attempt))`，
  附加字数上限为 `max(18, int(requested_budget * 0.35))`。
  保留原生 Historical Task Snapshot／无用户消息标记和 Critical Context，允许省略其他章节。
- 回答前根据受保护提示、最大的五个完整证据块、摘要预算及 96 tokens 预留／封装空间计算完整输入上限。
  若序列化后的 S 需要更多空间，则先提高上限。它不是统一的 1000／2000-token 上限，也不是等长比较。
  计算见 [`suite_run.py`](./suite_run.py)。
- 保留原始 system／任务，排除采集结束时的最终报告和内部元数据。评测问题与标准答案不会进入采集、
  摘要或决策请求。精确的后续问题构造见 [`suite.py`](./suite.py)。

以下主任务预算取自格式说明修正后的**最终评分记录**：

| 任务 | 证据块数 | 摘要正文上限 | 完整输入上限 |
| --- | ---: | ---: | ---: |
| payment | 10 | 256 | 4,496 |
| checkout_504 | 5 | 256 | 5,246 |
| server_error | 41 | 256 | 3,185 |
| build_token | 8 | 256 | 3,859 |

保留的支付任务早期 `budget.json` 记录为 4459；最终问题需要额外 37 tokens，最终 `results.json` 中的记录为 4496，
评分对照以此为准。冻结产物保留原貌，不回写修改。所有条件均满足其上限；纯 H 的 42 个上下文都短于 Full。
Top 3～5 每种机制的每组只有 9/12 个主任务上下文缩短。全部样例保留评分，平均节省不代表每个样例都节省。

## 评分

每次回答返回 `{"facts": {...}}`。字段按递归的精确类型和值规则检查，只有支付任务的 HTTP 状态码顺序可以忽略。
缺失、格式错误或计划中的失败条件记零分。先平均回答内字段，再平均同一轮次回答、同一任务轮次，
最后对任务等权平均。主任务和对照任务分别报告。

回答输入采用回答 API 实际返回的 `prompt_tokens`，包含 system／任务、压缩历史和后续评测问题。
摘要生成和 Jev 排名属于独立请求，不加入该指标。

## 复现层次与产物可用性

1. **冻结结果离线复核**：核验精确文件哈希、模型请求／响应和全部 1092 次评分，不调用任何模型 API。
2. **固定输入扩展／重跑**：`suite_fusion` 复用轨迹、摘要和排名，重新回答 H + Top 1～5，并保留其他八组。
   新分数可能变化；该命令不会重新回答全部十三组。
3. **重新采集并运行**：使用固定 Hermes 素材及 [README 命令](./README_ZH.md)。新的 agent 调用可能形成不同轨迹，
   因而复现的是协议，不保证结果逐字一致。

公开 Git 包含实验代码、任务定义、规则与整理后的结果，**不提交**原始支付轨迹、冻结语料及实际 API 记录。
精确复核需要本地产物包，目前不属于公开的一条命令即可复现的实验。不能替换为另一条支付轨迹，预期 SHA-256 为
`0f37e6510ffafd920d088452d8719026b00fd4e74f87f7dd1a42a85c8287e6f1`。

产物包位于 Git 仓库外：
`/Users/yuli/workspace/trajectory-runs/compaction-dual-summary-reproduction-20261016.tar.gz`。
其 SHA-256 为 `40ee93c9117dfe59cf0b4dc8887ba4b2c62fa16f3bc97f2dac6d536343f942a3`。
其中含 3187 个文件、相对路径 SHA-256 清单、环境元数据和 `verify.py`。
安装 ReMe 开发环境后，在 ReMe 仓库中运行：

```bash
# 在仓库外解压，替换为实际存放归档文件的目录。
export REPRO_DIR=/path/outside/repository
shasum -a 256 "$REPRO_DIR/compaction-dual-summary-reproduction-20261016.tar.gz"
tar -xzf "$REPRO_DIR/compaction-dual-summary-reproduction-20261016.tar.gz" -C "$REPRO_DIR"
PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}" python \
  "$REPRO_DIR/compaction-dual-summary-reproduction-20261016/verify.py"
```

预期结果：**核验 3187 个产物哈希、546 个上下文和 1092 次评分；零 API 调用**。
产物包内的 `corpus/`、`evaluation/`、`native/`、`native-source/`、`combined/`、`final/` 对应
[README 中的运行阶段](./README_ZH.md)。复用其中 H 摘要时传入 `--native-evaluation <bundle>/native-source`。

新运行需要在 `.env` 中配置 `LLM_API_KEY`、`LLM_BASE_URL`、`DECISION_MODEL_API_KEY`、可选的
`DECISION_MODEL_BASE_URL`，并在服务可用时设置 `DECISION_MODEL_NAME=jev-1.13.0` 以请求记录中的 Jev 版本。
使用独立 Python 环境、上表依赖版本、固定 Hermes checkout 与 tokenizer，以及新的输出目录。
不要提交 `.env`、原始记录或产物包。冻结结果离线复核不需要新的模型推理。
