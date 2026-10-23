# MobileMem-Omni 视觉推理评测

使用每个用户完整、按时间排序的原始对话，评测 ReMe Image 在官方 `visual_reasoning` 题目上的表现。
记忆与回答 Job 仅接收原始文本和图像，不接收数据集摘要、caption、标准答案、证据标注或题型。
官方 `multi_visual_reasoning` 不被重命名，也不纳入这个评测范围。

## 运行

安装两个插件，并按原目录结构解压官方图片：

```bash
pip install -e ".[as]" -e plugins/mobilemem -e plugins/mobilemem-judge
mkdir -p /path/to/omni/image
python -m zipfile -e /path/to/omni/image.zip /path/to/omni/image
export LLM_API_KEY="..."
export LLM_BASE_URL="..."
python -m benchmark.mobilemem.run --dataset /path/to/omni --output /path/to/exp-xxxx
```

[config.yaml](config.yaml) 默认使用 `qwen3.8-max`、4 个用户并发、16 个题目并发；
可通过 `--model`、`--user-concurrency`、`--query-concurrency` 覆盖。
每次运行创建 `<output>/mobilemem/<model>`，已有目录不会被覆盖。

## 评测设置

每个用户使用独立的新工作空间，按时间顺序通过多模态 `auto_memory` 摄入全部 session，然后更新一次索引。
每题使用新的 `agentic_answer` Agent，最多 30 轮，工具为 BM25 `search`、`read` 和 `read_image`。
检索范围包含 daily、digest 笔记及原始 session 正文；保存的原生图像附件与 Image ID 可供回答 Agent 重新读图。

[候选模型配置](../../plugins/mobilemem/src/reme_mobilemem/benchmark.yaml) 在记忆、回答和压缩阶段使用同一模型：
temperature 为 0，开启 thinking，输出预算 65,536，上下文为 1,000,000 token，最多 4,096 张图。
原生上下文比例保持 0.8/0.1。输入图片不缩放；MPO 保持既有的主图 PNG 转换。
数据集图片路径别名通过唯一 basename 对应原件。

问题使用官方 QA 模板，并提示通过证据工具作答。标准答案与证据仅交给独立的
[MobileMem Judge](../../plugins/mobilemem-judge/README.md)。默认采用 MemBase 可执行默认
`mobilemem-omni-judge` 评分模板，模型为 `qwen3.8-max`，temperature 为 0，关闭 thinking，输出预算 4,096。
报告包含二元 LLM-Judge 准确率及官方 token-overlap F1、BLEU-1。

## 结果

每个用户的 `workspace/` 保存笔记、原始 JSONL、图像及原生 AgentScope 轨迹。
`sessions/*.json` 与 `questions/*/` 保存响应、评分、指标和技术错误。
`summary.json` 汇总完成/应测题数、指标、记忆与回答 token 总量及平均值。
用量覆盖 provider 返回的压缩调用；缺失的 cache 字段保持未知。Judge 用量不计入方法成本。
原生中断与失败 Job 作为未评分的技术缺口保存；runner 不额外加入 fallback 或重试队列。

协议来源、数据版本和改编代码的完整 MIT 许可证见 [英文说明](README.md)。
