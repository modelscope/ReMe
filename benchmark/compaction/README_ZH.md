# 上下文压缩：固定摘要与原文证据选择

[English](./README.md) | **简体中文**

本实验使用 **14 个预设 query/answer 的合成任务模板**，按固定规则评分：4 个主任务，另有 10 个短任务或仅依赖问题的对照。
参见[任务、标准答案和固定规则](./STUDY_ZH.md)与[实验结果](./RESULTS_ZH.md)。

Hermes 通过实际 `read_file` 调用采集轨迹。随后比较 Full context、固定的通用 Qwen 摘要 S，以及
**Hermes 上下文压缩摘要 H（小预算版）**；S、H 分别追加 Jev Top 0～5 原文。评分时直接调用 Qwen，
没有恢复 Hermes 的工具循环或从归档中取回原文。生产功能 `compact_context` 与本实验独立。

模型、框架与运行环境版本、请求参数、产物哈希和离线复核要求见[实验设置与复现说明](./SETTINGS_ZH.md)。

## 运行

使用 ReMe 开发环境并安装可选依赖 `tokenizers`。轨迹采集和 Hermes 摘要生成需要独立的 Hermes 环境，
该环境也必须能导入 `tokenizers`。凭证从 ReMe 的 `.env` 读取：
`LLM_API_KEY`、`LLM_BASE_URL`、`DECISION_MODEL_API_KEY`，以及可选的
`DECISION_MODEL_NAME`、`DECISION_MODEL_BASE_URL`。
所有命令均需显式传入 `--live`；输出必须使用仓库外的新目录。

```bash
# 固定全部任务与标准答案，再采集 13 条新的只读轨迹。
# 复用固定的原始支付轨迹，作为第 14 个来源。
python -m benchmark.compaction.suite_collect --live \
  --hermes /path/to/hermes-agent \
  --hermes-python /path/to/hermes-environment/bin/python \
  --payment-trajectory /path/to/original/trajectory.full.json \
  --output /path/outside/repository/corpus

# 固定摘要 S 和 Jev 排名，再运行普通摘要的七组 Top-N 对照。
python -m benchmark.compaction.suite_run --live \
  --corpus /path/outside/repository/corpus/corpus.json \
  --tokenizer /path/to/cached/qwen/tokenizer.json \
  --output /path/outside/repository/evaluation

# 生成小预算设置下的 Hermes 上下文压缩摘要。
# 若 --native 已是完整目录，则复用其中全部固定摘要。
python -m benchmark.compaction.suite_native --live \
  --corpus /path/outside/repository/corpus/corpus.json \
  --evaluation /path/outside/repository/evaluation \
  --native /path/outside/repository/native-generations \
  --hermes /path/to/hermes-agent \
  --hermes-python /path/to/hermes-environment/bin/python \
  --tokenizer /path/to/cached/qwen/tokenizer.json \
  --output /path/outside/repository/combined-results

# 复用全部固定摘要、排名和 672 次回答，仅补充 H + Top 1～5。
python -m benchmark.compaction.suite_fusion --live \
  --corpus /path/outside/repository/corpus/corpus.json \
  --evaluation /path/outside/repository/evaluation \
  --combined /path/outside/repository/combined-results \
  --native /path/outside/repository/native-generations \
  --tokenizer /path/to/cached/qwen/tokenizer.json \
  --output /path/outside/repository/dual-summary-results
```

任务定义来自 Hermes commit `30463589eb54fa0f48724594cc0e98e6b995729b`（MIT 许可）。本次使用
`qwen3.8-max`，每个任务请求 3 轮摘要／排名，每个上下文回答 2 次：13 种方法共 **546 个上下文、1092 次回答**。
模型请求最多同时运行 4 个。原始文件、会话、API 请求／响应、代码快照和逐字段评分均保留在 Git 仓库外，已有运行不会被覆盖。

S、H 在各自五种融合条件中逐字不变，两种机制使用相同的 Jev 选择结果。Top N 是按概率严格降序选出的前 N 块，
不设置概率阈值，不跳过候选块，也不截断块；入选块按来源顺序排列。若可用块少于 N，则全部保留，
并用 `actual_n` 记录实际数量。原支付轨迹有 10 块，最多 Top 10；本实验测试 Top 1～5，各任务的块数不同。

H 复用 Hermes 的上下文压缩摘要生成流程，并采用小预算设置：`legacy` 模板、与 S 相同的正文预算上限、
额外字数约束、原生来源校验，以及统一的摘要正文封装。实验直接生成摘要，绕过自动触发和首尾窗口选择，
且**必须实际缩短输入**。具体设置与预检记录说明见[实验方案](./STUDY_ZH.md)。

本次曾修正评测问题的格式说明，而 Hermes 摘要使用修正前的来源文件。因此扩展该次运行时，需额外传入
`--native-evaluation /path/to/pre-amendment/evaluation`。扩展程序会校验来源哈希，且只允许保留用于评分的
`exam` 字段不同；摘要生成器不会接收这个字段。
