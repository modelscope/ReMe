# 基于决策模型的上下文压缩

`compact_context` 为旧工具结果生成可恢复的预览建议：判断证据对当前任务是否仍有用，保留工具调用和不确定的证据。
原始历史由宿主持有。流程使用通用 `as_decision_model` 接口，当前 `agentscope` 适配器连接 TypeSafe/Jev。

![证据观测、保守选择、预算检查和原文恢复](../figure/decision-context-compaction.svg)

## 一次压缩如何工作

1. **宿主先归档。** 提供 AgentScope 2.x JSON 消息、`goal`、可选的 `next_action`、只读工具允许列表，以及
   `source_refs`：原始调用 ID 到归档来源的映射。引用是宿主定义的标识；ReMe 不打开、验证或创建归档。
   宿主必须在应用建议前保存原始历史，并提供能根据引用取回原文的工具。没有引用的配对不参与压缩。
2. **确定性保护。** 按唯一 ID 配对 `tool_call` 和 `tool_result`。第一条、system、最近和显式保护的消息及调用保留。
   未完成或失败的调用、非文本结果、非法输入、工具名不一致和不明确的配对保留。`eligible_tool_names` 默认为空。
3. **展示有界证据。** 每批只携带本批候选的工具名、输入、结果头尾片段、字符数和完整性标记，同时携带目标、
   下一步行动和有限的首条、system、保护及近期文本。thinking 不发送。预览可能包含源码等数据，宿主应在推理前处理敏感内容。
4. **每对一个问题。** 判断“这份证据是否包含继续正确执行任务所需的信息”，不再判断能否重新获取。
   截断或缺失信息代表不确定。单个证据放不进请求预算时保留，不移除观测内容后继续盲判。
5. **只替换明确无关的结果。** 概率 `<= drop_threshold`（默认 `0.1`）时，允许替换为原文头尾片段和恢复引用。
   更高概率、缺失或非法答案保留原文。供应商错误和超时保留受影响证据；外部取消在请求清理后向上传播。

工具调用和消息都不删除。新结果只有更短时才替换。用户与 assistant 文本、thinking、元数据和输入原文不改变。
不可丢失的约束、审计回执和关键证据应显式保护，不能只依赖概率。默认阈值是保守起点，不代表已经校准。

## 配置与调用

```bash
pip install "reme-ai[core,decision]"
export DECISION_MODEL_API_KEY=your-typesafe-api-key
export DECISION_MODEL_BACKEND=agentscope
# 可选：DECISION_MODEL_NAME、DECISION_MODEL_BASE_URL
```

CLI 也从 `.env` 读取 `DECISION_MODEL_*`，详见[决策模型配置](./configuration.md#决策模型配置)。
省略模型名或配置为 `null` 时使用 SDK 默认模型。

在一个终端启动服务：

```bash
reme start config=decision_compaction
```

在另一个终端调用，引用应已由宿主归档并能够解析：

```bash
reme compact_context \
  goal='修复支付重试' next_action='检查重试实现' \
  eligible_tool_names='["search_code"]' source_refs='{"c1":"archive/demo/c1"}' \
  options='{"preserve_recent_messages":1}' \
  messages='[{"role":"user","content":[{"type":"text","text":"修复重试"}]},{"role":"assistant","content":[{"type":"tool_call","id":"c1","name":"search_code","input":"{\"path\":\"icons\"}","state":"finished"},{"type":"tool_result","id":"c1","name":"search_code","output":"旧图标搜索结果","state":"success"}]},{"role":"user","content":[{"type":"text","text":"接下来检查支付代码"}]}]'
```

短结果可能因为恢复标记反而更长而保持不变。配置继承默认服务和后台 Job；嵌入宿主时，可参考
[集成测试](https://github.com/agentscope-ai/ReMe/blob/main/tests/integration/test_decision_compaction.py)只装配压缩 Job 与决策组件。

## 主模型 token 预算

决策请求的估算预算与压缩后主模型输入预算独立。使用 `max_output_tokens` 时，宿主必须在构造 Step 时注入同步函数
`token_counter(messages)`，按实际模型输入格式计算 token，包含 system、工具定义和消息封装。函数必须返回非负整数。
缺少计数函数时在推理前报错。ReMe 的检索分词器不能代替模型 token 计数器。

```python
step = CompactContextStep(as_decision_model=decision_model, token_counter=count_model_input)
response = await step(
    messages=snapshot,
    goal="修复重试",
    next_action="检查补丁",
    source_refs=archive_refs,
    eligible_tool_names=["read_file"],
    options={"max_output_tokens": 32000},
)
```

已经满足预算时不调用模型。否则只在低概率候选内按概率从低到高替换，满足预算即停止；替换必须同时减少文本大小和
宿主 token 计数。不会为了满足预算删除必要或不确定的证据。仍然超限时返回 `reason="budget_exceeded"`、
`budget_met=false`，宿主应先执行摘要等后续策略。未指定预算时处理所有符合条件的低概率结果，`budget_met=null`，
由宿主自行检查最终输入。

## 返回值与默认配置

标准 Response 的 `answer` 包含 `schema_version=2`、建议 `messages`、`changed`、`reason`、`budget_met`、
`decisions` 和 `stats`。每个决策记录原始 `call_id`、内部 `id`、动作 `keep` / `preview`、`probability`、
`reason` 和 `source_ref`。原因区分保护、不确定、未观测、非法答案、供应商错误、超时和没有节省。
统计包括前后大小及宿主 token 数、候选和保护数量、最大批次状态估算 token、请求数、usage 和耗时，也写入响应元数据。

| 配置 | 默认值 | 含义 |
| --- | --- | --- |
| `drop_threshold` | `0.1` | 只有不高于此概率的结果允许替换为预览 |
| `preserve_recent_messages` | `6` | 保护最近的消息数 |
| `evidence_chars` | `2000` | 每个输入、结果预览或近期文本的字符上限 |
| `preview_chars` | `300` | 建议结果保留的头尾片段字符上限，不含恢复标记 |
| `max_state_tokens` | `25000` | 决策状态的估算上限 |
| `max_request_tokens` | `30000` | 状态和问题的估算上限，含 256 token 开销预留 |
| `max_output_tokens` | `null` | 可选的宿主计数预算 |
| `max_concurrency` | `4` | 最大并发请求数 |
| `total_timeout_seconds` | `30` | 包含排队的总体请求超时 |

## 验证

两个集成场景分别模拟支付重试排障和副本延迟调查，让重要源码、日志与已经结束的无关任务竞争。
配置凭证后显式运行：

```bash
REME_RUN_DECISION_INTEGRATION=1 pytest tests/integration/test_decision_compaction.py -v -s
```

只有模型请求调用外部服务，历史中的工具不会执行。这些用例验证行为，不证明通用任务成功率。
真实 trajectory 评测应对比近期保留和纯规则预览，同时测量恢复次数、继续执行的质量、时延、总成本和 token 节省。
ReMe 不会自动生成摘要或写入长期记忆。

## 压缩策略对比

[Benchmark 方案与结果](https://github.com/jinliyl/ReMe/blob/a013411457667ee062902252d43910bf8c87dc17/benchmark/compaction/RESULTS.md)使用 HotpotQA 公开验证集中的 **30 道不同题目**，均有人工标准答案和句子级支持证据。
固定抽取 15 道桥接推理、15 道比较问题，题目之间的证据文章不重叠，不再使用标识符变体。
Hermes 实际读取每题的十篇文章，形成 30 条完整 trajectory、300 次工具调用。
标准答案和证据标签放在工具工作区之外，只供确定性评分；最终助手答案不进入待压缩历史。

三个压缩组统一使用 **3600-token 完整输入上限**，包含原始 system、任务、证据、评测提示和消息封装。
Full context 保留公开 API 消息字段，作为允许超限的参考。Hermes 数据库快照和内部推理字段不进入模型输入。
融合先用最多 40% 的可用空间保留 Jev 筛选的原文，再用全部剩余空间总结其余证据。

| Method | Input tokens | Reduction | Answer EM |
| --- | ---: | ---: | ---: |
| Full context | 5,482 | 0.0% | 61.7% |
| Jev | 2,606 | 52.5% | 51.7% |
| Summary | 2,686 | 51.0% | 61.7% |
| Jev + Summary | 3,043 | 44.5% | 60.0% |

每组 60/60 个有效上下文、120 次回答；实际压缩输入为 2392–3447 tokens，全部低于上限。
融合比全量少用 44.5% 的后续输入，答案 EM 相差 1.7 个百分点；但纯摘要同样达到 61.7%，输入更少，
**尚未验证“融合优于两个单独方案”**。支持证据 F1 分别为全量 83.0%、Jev 67.2%、摘要 75.5%、融合 80.0%。
这些是点估计，不代表统计等价；表中节省不包含压缩本身的额外消耗。

主要指标为官方答案 Exact Match；答案 F1、支持证据及联合得分单独报告，不根据结果切换主要指标。
每题每组生成两次、每个上下文回答两次，共 240 个上下文和 480 次回答。预算超限或生成失败计为失败。
评测直接调用 Qwen，没有运行 Hermes 代理继续执行，也不允许恢复被丢弃的原文。
该融合策略仅在实验脚本实现，未改变上述 `compact_context` 生产契约。
