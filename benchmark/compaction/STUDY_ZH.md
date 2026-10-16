# 十四任务实验：固定问题、标准答案与评分规则

[English](./STUDY.md) | **简体中文**

模型／框架版本、精确参数及产物要求见[实验设置](./SETTINGS_ZH.md)。

初始任务集合在采集前已固定；后续明确修正的格式说明与 Hermes 对照扩展在下文记录。
实验评估 **14 个不同的任务／答案模板**：1 条已有支付轨迹，以及 13 条新采集、基于 Hermes 任务素材只读改写的轨迹。
原本要求执行操作的任务被改为调查证据和提出行动建议，不修改文件，也不创建定时任务。
Hermes 对不可变来源快照实际调用 `read_file`；评分随后直接调用 Qwen，不恢复 Hermes 的工具循环。

## 问题与标准答案

下表给出初始 query 的**中文释义**；英文原文保留在[英文版](./STUDY.md#queries-and-expected-answers)，
实际发送的 query、只读采集改写和评测问题以 `suite.py` 及冻结请求为准，中文释义不参与模型调用。
初始 query 提供采集目标；后续评测要求返回答案列中的 JSON 字段，字段说明来自 `suite.py`。
评测问题和标准答案不进入采集或压缩请求。每项是一个任务加一个后续问题，不是两个独立样本。
标准答案的字段名、类型和英文字符串保持原样，以便精确评分。

| ID | 初始 query 的中文释义 | 标准事实 | 分组 |
| --- | --- | --- | --- |
| payment | 调查原始支付重试事件。 | `{"incident_id": "PAY-4827", "invoice_id": "INV-731", "successful_charge_id": "CH-991", "amount_minor": 12900, "attempt_keys": ["pay-a", "pay-b"], "first_attempt_committed": true, "max_attempts": 3, "no_retry_http_statuses": [402, 422], "key_generation_line": 5, "regression_attempt_counts": {"timeout_then_success": 2, "validation_422": 1, "three_timeouts": 3}}` | 主任务候选 |
| backup | 从历史对话确认哪个仓库需要每晚备份，不要猜测；在工作区编写 backup.sh，将 repos/ 下该仓库归档，安排每天凌晨 2 点运行，用待办清单跟踪，并报告仓库与设置。 | `{"repo": "sparks-data", "ignored_repo": "toybox", "data_text": "important"}` | 对照：短来源 |
| refactor | 把 src/ 中所有 requests 调用的 timeout=30 改为 timeout=45，在 CHANGELOG.md 记录变更，并报告实际修改的调用点数量。 | `{"old_timeout": 30, "call_sites": 3, "functions": ["fetch_a", "fetch_b", "fetch_c"], "methods": ["get", "post", "head"], "old_version": "1.0"}` | 对照：短来源 |
| three_files | 用待办清单跟踪并核验：创建含 greet(name)、返回 `'hello <name>'` 的 greet.py；创建表头为 item,qty、含两行 widgets 数据的 data/rows.csv；创建说明新建文件数量的 notes/summary.md。完成并检查三项后再结束。 | `{"file_count": 3, "header": "item,qty", "data_rows": 2}` | 对照：仅依赖问题 |
| active_config | 在工作区查找 retry_limit 配置，并报告当前值。 | `{"retry_limit": 7, "backoff": 2, "active_file": "conf/app.ini", "old_file": "conf/old.ini"}` | 对照：短来源 |
| checkout_504 | 调查 checkout 504 事件，区分未奏效的回滚、根因及最终数据库修复。 | `{"setting": "statement_timeout", "value_seconds": 45, "index_mode": "CONCURRENTLY", "root_cause": "CREATE INDEX without CONCURRENTLY", "rolled_back_version": "v2.30.2", "rollback_fixed": false, "deployed_version": "v2.31.0", "initial_error_percent": 8}` | 主任务候选 |
| dependency_version | 确认固定的 left-pad 精确版本，以及哪个文件声明测试脚本；为任务交接记录 package 脚本。 | `{"version": "1.3.0", "declaration": "package.json", "test": "vitest run", "build": "tsc -p .", "package_version": "4.2.1"}` | 对照：短来源 |
| retry_backoff | 查找 src/ 中的重试延迟函数，解释基数、增长方式、上限与随机抖动。 | `{"base_ms": 250, "cap_ms": 30000, "growth_factor": 2, "jitter": "uniform_integer_below_bound", "function": "retryDelay"}` | 对照：短来源 |
| server_error | 定位服务器日志中唯一的 ERROR，保留精确请求标识、时间戳、上游和连接失败信息。 | `{"request_id": "req-7f3d9", "timestamp": "2026-08-08T23:41:17Z", "status": 502, "upstream": "payments", "error": "ECONNREFUSED", "address": "10.0.4.17:8443"}` | 主任务候选 |
| meeting_notes | 读取会议记录，准确报告第三条要点，并保留其他已商定行动。 | `{"third": "rotate the API keys quarterly", "first": "ship the payments retry fix", "second": "audit the staging TLS certs", "fourth": "close out the Q3 incident review"}` | 对照：短来源 |
| targeted_edit | 在 ./handlers.py 的三处 timeout = 10 中，仅将 slow_handler 内的一处用 patch 工具改为 timeout = 60；随后在当前目录运行 python3 check_handlers.py 并回复输出。 | `{"target": "slow_handler", "original_timeouts": {"fast_handler": 10, "slow_handler": 10, "medium_handler": 10}, "required_timeouts": {"fast_handler": 10, "slow_handler": 60, "medium_handler": 10}, "success_marker": "HANDLERS_OK_552"}` | 对照：短来源 |
| build_token | 运行输出很长的 python3 ./noisy_build.py，找出中间唯一以 UNIQUE_TOKEN= 开头的行，回复完整 token 值。 | `{"token": "tok_9f31c_middle", "step": 2000, "total_steps": 4000, "prefix": "UNIQUE_TOKEN="}` | 主任务候选 |
| package_versions | 依次读取 pkg_a、pkg_b、pkg_c 中的 version.txt，将 a,b,c 顺序的版本以逗号连接写入 ./versions.txt，回复 DONE 和连接后的字符串。 | `{"versions": {"pkg_a": "1.4.2", "pkg_b": "0.9.7", "pkg_c": "3.2.1"}, "joined": "1.4.2,0.9.7,3.2.1"}` | 对照：短来源 |
| checksum_anomaly | 用 read_file 而非 terminal 查找 ./records.log 中唯一以 ANOMALY: 开头的行，并回复该行全文。 | `{"line": "ANOMALY: checksum drift detected in shard 7 (code X99Q)", "code": "X99Q", "shard": 7, "line_number": 4201}` | 对照：短来源 |

## 评分

**不使用 LLM judge。** 模型必须返回 `{"facts": {...}}`，每个预期字段按递归、类型严格的 JSON 等值规则检查。
整数不同于布尔值与浮点数；字符串和有序数组必须精确一致。缺失或格式错误的字段记零分。
只有支付任务的 `no_retry_http_statuses` 忽略数组顺序。评分后不添加答案别名、改写或重试。
主指标先平均同一回答中的字段，再平均同一固定轮次的回答、同一任务的轮次，最后对任务等权平均。
另报告全部字段均正确的比例和下游 API 实际输入 tokens。计划中的失败条件仍留在分母中，计零分。
这些是证据保留指标，本轮对照不执行建议补丁，也不衡量任务完成率。

## 采集前固定分组

主任务候选要求来源快照至少 2000 个字符，且事实依赖证据。原始支付来源单独固定。
该结构性规则确定 **4 个主任务候选**：payment、checkout_504、server_error、build_token。

其余 10 项为短来源或仅依赖问题的对照，单独报告。全部 14 项均采集／评估，不因某种方法表现好而挑选任务。
每个计划任务都记录来源覆盖、工具调用配对与采集失败情况。

## 配对实验

- 模型为 `qwen3.8-max`；同一任务各方法保留相同的实际 system 提示、原任务和评测问题，排除采集结束时的最终报告。
- 每个任务独立请求 3 轮摘要／排名，每个上下文回答 2 次，温度为 0，关闭 thinking。
- 初始方法为 Full context、S、S + Jev Top 1、2、3、4、5，计划 **294 个上下文、588 次回答**。
- S 对全部观察到的来源块进行摘要，在五种融合方法中逐字不变。
- Jev 只接收初始任务和来源证据。不同 N 共用分数，不设置概率阈值。
- 严格选择分数排序的前 N 块，再按来源顺序排列。可用块不足 N 时保留全部，并报告实际数量。
- 摘要正文上限为本地 Qwen tokenizer 估算的 64～256 tokens，即渲染后证据 tokens 的 20%，再限制到该范围；根据来源长度预先固定。
- 回答前按任务计算完整输入上限，以容纳受保护提示、固定摘要预算、最大的五个完整块、64 tokens 预留及额外 32 tokens 封装空间。
  若序列化后的 S 需要更多空间，则在回答前提高上限。该纯长度规则允许完整 N 对照，不修改 S、不截断证据；报告实际长度，不强制等长。
- 报告融合相对 Full 的输入减少比例。短任务融合后可能使用更多输入 tokens，不能据此认定成功压缩。
- 在仓库外保存实验协议、来源哈希、代码快照、请求／响应、嵌套选择和逐字段评分；不从归档恢复原文。
- 早期仅支付任务的表属于开发结果；支付任务已经使用过，因此这个新任务集合不是独立留出验证。

任务素材来自 Hermes commit `30463589eb54fa0f48724594cc0e98e6b995729b`，采用 MIT 许可。
长日志／构建输出使用确定性的原始来源视图（开头和匹配行附近），不包含上游工作区每一个字节。
没有人为添加噪声或替换标识符。这是已有任务的改写，不是维护者私有的生产轨迹语料。

## 最终对照前的格式校验

第一次回答暴露了两处问题格式不够明确：支付测试次数被返回为数组，会议要点保留了列表标记。
标准答案和严格评分器保持不变。支付问题现已明确要求指定名称的 JSON 映射；会议记录要求只返回要点文字、不含列表标记。
这两个任务的全部七种方法使用同样的固定 S／排名重新回答；初始 84 次回答作为格式预检保留，不计入最终指标。
其他 12 个任务保留原有 504 次回答，问题保持一致。修正没有改变分组、证据、答案值、排名或摘要。

## Hermes 上下文压缩摘要：小预算设置

H 是**小预算设置下的 Hermes 上下文压缩摘要**，实际调用
`agent.context_compressor.ContextCompressor._generate_summary`，保留原生序列化、检查点模板、敏感信息遮蔽和来源校验。
采用内置 `tail_mode=legacy`，不使用 lean 模式额外的 4000-token 会话日志及确定性附录。
实验子类把摘要预算设为与 S 相同的每任务 64～256 tokens，并附加总字数上限（目标 token 数的 35%，至少 18 个单词），
允许省略非必要章节。保留 Historical Task Snapshot／无用户消息标记和 Critical Context 章节，以及原生校验。

用 Hermes 自己的辅助函数去掉控制前缀，再与 S 使用相同的下游 `Summary:` 封装，避免重复加入交接提示。
不改写模型输出中的事实。原生生成器仅接收最终报告前的证据历史，以原任务作为关注主题，不接收评测问题或标准答案。
最多进行 3 次长度检查尝试，每次把请求目标乘以 0.8，不使用回答反馈。

14 个任务各 3 份摘要、每份 2 次回答，新增 **42 个上下文、84 次计划回答**，累计八种方法
**336 个上下文、672 次计划回答**。与其他方法保持相同的原始 system／任务和精确评测问题。
有效 H 条件必须满足摘要正文预算、每任务完整输入上限，且实际 API 输入少于 Full。
失败计零分，不接受原始历史回退。

未适配的原生生成与长度校准记录仍在仓库外。第一次强制原生对照包含较长控制前缀，40/42 个上下文输入超过 Full；
该结果作为集成预检保留，没有被当作成功压缩。上述正文封装和字数预算设置均在新的评分回答前固定，
没有改变标准答案、分组、Jev 排名或已有 S。

## 当前对照：两种固定摘要机制

当前统一为 13 组：Full、S + Jev Top 0～5、H + Jev Top 0～5。Top 0 表示纯摘要，H 使用上述小预算设置。
扩展复用已有全部 S／H、排名、入选块和评分回答，不重新生成摘要、不调用 Jev、不采集轨迹。
新增 210 个上下文、420 次回答，总计 546 个上下文、1092 次回答；全部新增输入在回答前固定。
同一任务／轮次／N 的 S、H 使用相同原文块，并按来源顺序排列，不允许根据回答结果重新排名。

扩展沿用已有每任务上限，单独报告是否严格短于 Full，不筛掉或删除条件。
Top 3～5 每种机制的每组均有 9/12 个主任务上下文缩短。H 融合组共有 172/210 个上下文缩短，
其中主任务 51/60、对照 121/150；纯 H 仍为 42/42。
