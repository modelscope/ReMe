# 基于决策模型的上下文压缩

长任务会积累大量工具调用：读过的源码、过期的搜索结果、重复查询的日志、已经结束的支线任务。
`compact_context` 根据**下一步要做什么**，判断旧工具调用是否仍然有用，以及它的完整输出是否必须保留。
它返回一份建议的消息快照和逐调用决策，由宿主决定是否应用。

这一流程通过 `as_decision_model` 接口调用概率决策模型。当前 `agentscope` 适配器使用 AgentScope 的
TypeSafe/Jev 实现；替换供应商时，Job 和压缩策略仍然使用同一个接口。

![决策模型上下文压缩流程：保护规则、观测视图、双问题决策和宿主应用](../figure/decision-context-compaction.svg)

## 一次压缩如何工作

1. **宿主先归档原始历史。** 宿主提供 AgentScope 2.x 的 JSON 消息快照、当前 `goal`、允许处理的工具名和保护列表。
   ReMe 不负责归档，也不会替宿主更新运行中的 Agent 状态。只有原始记录可恢复时，宿主才应应用删减建议。
2. **用确定性规则挑选候选。** 按调用 ID 配对 `tool_call` 与 `tool_result`。调用必须为 `finished`，结果必须为
   `success`，工具必须在显式允许列表中，输出必须全部是文本。重复 ID、缺失配对、反向配对和非法 JSON 输入不会参与决策。
3. **建立有限的观测视图。** 发送当前目标、对话文本、工具名、截短后的输入和结果字符数。工具输出正文与 thinking
   不进入决策请求。观测超预算时，逐步缩短输入和旧文本、移除旧的纯文本消息或合并旧调用记录；返回的会话原文不因此改变。
4. **每个候选问两个二分类问题。** `call_<id>` 判断“调用及其输入对下一步是否仍然重要”，`result_<id>` 判断
   “完整输出是否必须原样保留，之后再检索是否不够”。问题成对分批，每批携带相同观测视图，在并发和总超时约束内执行。
5. **全部批次成功后重建快照。** 校验每个答案的类型和概率范围，再在消息的深拷贝上应用决策。缺少答案、非法概率、
   任意批次失败或超时都会使调用失败，不返回部分压缩结果。宿主应继续使用已保存的原始快照。

## 两个概率如何变成动作

设保留阈值为 `t`，默认 `0.5`。先判断结果，再判断调用：

| 条件 | 动作 | 对返回快照的影响 |
| --- | --- | --- |
| `p_result >= t` | `keep` | 保留调用及完整结果，即使 `p_call` 较低 |
| `p_result < t` 且 `p_call >= t` | `drop_result` | 保留调用，将长文本结果替换为前缀和省略标记 |
| 两个概率都 `< t` | `drop_call` | 同时移除调用和结果；仅移除因此变空的消息 |

`drop_result` 的默认前缀为 300 个字符，标记提示从归档历史恢复全文。只有新文本更短时才替换，所以该动作对短输出可能不产生变化。
用户文本、assistant 文本、thinking 和未被修改的块字段保留原样。

以下内容优先受规则保护，不受概率阈值影响：

- 第一条消息、最近 `preserve_recent_messages` 条消息，以及 `protected_message_ids` 指定的消息。配对的任一端受保护，整对保留。
- `protected_call_ids` 指定的调用，以及不在 `eligible_tool_names` 中的工具。默认允许列表为空，因此默认不会压缩任何工具。
- 未完成或失败的调用、非纯文本输出、工具名不一致的配对。重复或缺失 ID 的块也不会删除，但不一定出现在 `decisions` 中。

允许列表应由宿主限定为安全的只读工具，ReMe 不会根据工具名自动识别副作用。
对于必须保留的审计记录、变更回执或关键证据，宿主应显式保护，不能只依赖语义概率。

## 配置与服务调用

安装并配置凭证：

```bash
pip install "reme-ai[core,decision]"
export DECISION_MODEL_API_KEY=your-typesafe-api-key
export DECISION_MODEL_BACKEND=agentscope
# 可选：DECISION_MODEL_NAME、DECISION_MODEL_BASE_URL
```

`.env` 也可以配置上述 `DECISION_MODEL_*` 变量，backend 使用 `agentscope`，完整设置见
[决策模型配置](./configuration.md#决策模型配置)。省略模型名或配置为 `null` 时使用适配器的 SDK 默认模型。

在一个终端启动服务：

```bash
reme start config=decision_compaction
```

在另一个终端调用。以下短示例展示请求格式；复杂样例见本文后面的集成用例：

```bash
reme compact_context \
  goal='修复支付重试逻辑，之前完成的图标搜索已无关' \
  eligible_tool_names='["search_code"]' \
  options='{"preserve_recent_messages":1}' \
  messages='[{"id":"m0","role":"user","content":[{"type":"text","text":"保留支付代码，清理旧图标搜索"}]},{"id":"m1","role":"assistant","content":[{"type":"tool_call","id":"c1","name":"search_code","input":"{\"pattern\":\"logo\",\"path\":\"web/icons\"}","state":"finished"},{"type":"tool_result","id":"c1","name":"search_code","output":"旧任务的图标路径列表","state":"success"}]},{"id":"m2","role":"user","content":[{"type":"text","text":"现在只处理支付重试"}]}]'
```

`decision_compaction` 继承默认服务配置和其他 Job，因此常规后台任务也会启动。
需要嵌入宿主进程时，可像集成测试一样只装配 `compact_context` Job 和它的决策组件，不启动其他工作流。

标准 Response 的 `answer` 包含：

- `schema_version`、`messages`：版本与建议快照；`changed`、`reason`：是否实际改变，以及 `compacted` / `no_change` / `no_candidates`。
- `decisions`：内部配对 ID、原始 `call_id`、动作、原因，以及参与推理时的 `keep_call` / `keep_result` 概率。
- `stats`：前后消息数和字符数、候选与保护配对数量、观测视图的估算 token 数及缩减阶段、请求数、供应商 usage 和耗时。
  同一份统计也位于 `response.metadata.compaction`。

宿主应检查 `success`，使用自己的 tokenizer 重新计算最终上下文预算，再选择应用建议、继续压缩或恢复原始记录。
压缩不会自动生成摘要、写入长期记忆或执行历史中的工具。

## 预算、并发和超时

| `options` 字段 | 默认值 | 作用 |
| --- | --- | --- |
| `keep_threshold` | `0.5` | 两个问题共用的保留阈值 |
| `preserve_recent_messages` | `6` | 原样保护最近的消息，按消息而非轮次数计数 |
| `max_state_tokens` | `25000` | 观测视图的估算 token 上限 |
| `max_request_tokens` | `30000` | 每批观测与问题的估算 token 预算，包含 256 token 的开销预留 |
| `truncate_head_chars` | `300` | `drop_result` 保留的文本前缀长度 |
| `max_concurrency` | `4` | 同时运行的决策请求上限，范围 1–32 |
| `total_timeout_seconds` | `30` | 所有决策请求及其排队等待的总超时 |

组件层的 `timeout`、`max_retries`、`retry_delay` 控制单次供应商请求及重试。
内置压缩配置分别为 10 秒、1 次重试、0.5 秒初始退避。预算使用本地估算器，不等于供应商计费 token，也不等于宿主模型的上下文预算。
观测无法装入预算，或一对问题也放不进单批请求时，调用失败，由宿主保留原始快照。

## 两个真实模型集成场景

[集成测试源码](https://github.com/agentscope-ai/ReMe/blob/main/tests/integration/test_decision_compaction.py)
提供两个合成的长任务场景。工具调用及其返回值均为测试数据，历史中的部署、回滚、数据库查询不会实际执行；
只有决策请求使用真实的 TypeSafe/Jev API。

| 场景 | 当前任务与关键候选 | 干扰与保护边界 |
| --- | --- | --- |
| 支付重试缺陷修复 | 下一步根据已读源码和测试原文生成精确补丁，验证相关源码与测试结果被保留 | 已完成的主题 CSS、图标搜索、过期库存查询应有可淘汰项；显式保护账单证据与审批回执，保留失败、运行中、重复 ID 和最近消息 |
| 数据库复制延迟排障 | 下一步引用事件日志及 WAL 位点原文编写根因报告，验证关键日志与数据行被保留 | 混入历史营销报表、旅行天气和退役系统压测；保护审计审批、回滚回执、非文本图表、失败查询和最近消息 |

两个用例都检查：真实推理按批执行、至少移除一个无关调用、关键候选完整保留、受保护记录和会话文本不变、
原始输入与临时归档不变，以及输出字符数实际下降。模型具有不确定性，语义断言可能揭示模型或配置的变化；测试不会伪造概率来保证通过。

2026-10-15 使用本地配置的 TypeSafe/Jev 端点实测，两例均通过，结果如下。数字按 JSON 字符数统计，不是 token 节省率：

| 场景 | 压缩前字符数 | 压缩后字符数 | 减少比例 | 被移除的无关调用 | 决策请求数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 支付重试缺陷修复 | 39,438 | 12,738 | 67.7% | 3 | 2 |
| 数据库复制延迟排障 | 51,485 | 12,828 | 75.1% | 4 | 2 |

显式授权真实 API 调用后运行：

```bash
REME_RUN_DECISION_INTEGRATION=1 \
  pytest tests/integration/test_decision_compaction.py -v -s
```

测试读取环境变量或仓库根目录 `.env`，环境变量优先；未显式启用时直接跳过，未配置 API key 时也跳过。
输出仅包含合成场景的动作、概率、字符数和 usage；工作区及原始快照放在 pytest 的临时目录中。
实际节省比例依赖任务历史、目标和模型判断，不能由这两个用例推导通用收益。

## 适用边界

决策模型只能看到有限观测视图，无法核查被省略的工具输出内容。目标写得不完整或工具描述不足时，判断可能遗漏重要信息。
宿主需要给出明确的下一步目标，为不可丢失的信息设置保护，并在应用后继续保留可恢复的原始历史。
该策略适合减少旧工具轨迹的体积；它不提供自动触发、最终 token 预算保证、摘要生成或归档存储。

接口与实现分别见 [Compaction schema](https://github.com/agentscope-ai/ReMe/blob/main/reme/schema/compaction.py)、
[候选配对与重建](https://github.com/agentscope-ai/ReMe/blob/main/reme/steps/compaction/messages.py)、
[观测与分批](https://github.com/agentscope-ai/ReMe/blob/main/reme/steps/compaction/state.py) 和
[Job Step](https://github.com/agentscope-ai/ReMe/blob/main/reme/steps/compaction/compact_context.py)。
