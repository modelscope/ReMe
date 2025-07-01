# 金融分析师Agent

一个智能的金融分析师Agent，能够通过搜索和分析构建金融知识图谱，发现金融实体之间的逻辑关系。

## 功能特性

- 🔍 **智能搜索**: 使用大模型和搜索工具发现金融实体关系
- 🧠 **知识图谱构建**: 自动构建和更新金融知识图谱
- 🔗 **关系分析**: 分析正向、负向、中性关系
- 📊 **可视化**: 生成交互式知识图谱可视化
- 🔄 **迭代优化**: 支持多轮迭代，不断丰富知识图谱
- 📝 **数据导出**: 支持JSONL格式导出

## 安装

1. 克隆项目并安装依赖：
```bash
pip install -r financial_agent/requirements.txt
```

2. 设置环境变量：
```bash
export OPENAI_API_KEY="your_openai_api_key"
export OPENAI_BASE_URL="your_openai_base_url"
export DASHSCOPE_API_KEY="your_dashscope_api_key"
```

## 快速开始

### 基本使用

```python
from financial_agent import FinancialAgent

# 创建Agent
agent = FinancialAgent(model_name="qwen-max-2025-01-25")

# 初始实体列表
init_entities = ["美元债务", "美债利率", "美元指数", "黄金", "石油"]

# 执行知识图谱构建
stats = agent.execute(
    init_entity_list=init_entities,
    dump_file_path="金融知识图谱.jsonl",
    max_iter=10,
    search_strategy="mixed"
)

print(f"构建完成！总实体数: {stats['total_entities']}, 总关系数: {stats['total_relations']}")
```

### 运行示例

```bash
python financial_agent/example.py
```

## 核心组件

### FinancialAgent

主要的金融分析师Agent类，负责：
- 搜索和分析金融实体关系
- 构建和更新知识图谱
- 提供查询接口

### FinancialRelation

金融实体关系的数据结构：
```python
{
    "input_entities": ["实体1", "实体2"],
    "output_entities": ["实体3", "实体4"],
    "relation": "正向、负向、中性",
    "reasoning": "关系推理过程",
    "source": "信息来源",
    "confidence": "置信度(0-1)",
    "timestamp": "时间戳"
}
```

### KnowledgeGraphBuilder

知识图谱构建器，提供：
- 关系去重和验证
- 实体别名管理
- 图谱查询和统计
- 可视化生成

## 配置选项

### 搜索策略

- `"general"`: 通用搜索，分析多个实体间的关系
- `"pairs"`: 实体对搜索，专注于特定实体对
- `"mixed"`: 混合策略，结合两种方法

### 模型配置

支持多种大模型：
- `qwen-max-2025-01-25`
- `qwen3-32b`
- 其他OpenAI兼容模型

## 输出格式

### JSONL文件格式

每行一个JSON对象，包含完整的金融关系信息：

```jsonl
{"input_entities": ["美债利率", "美元债务"], "output_entities": ["美元指数"], "relation": "负向", "reasoning": "美债利率上升和美元债务增加会导致美元走弱", "source": "金融分析报告", "confidence": 0.85, "timestamp": "2024-01-15 10:30:00"}
{"input_entities": ["石油价格", "美元指数"], "output_entities": ["通胀预期"], "relation": "正向", "reasoning": "石油价格上涨和美元走弱会推高通胀预期", "source": "经济分析", "confidence": 0.78, "timestamp": "2024-01-15 10:31:00"}
```

### 可视化输出

生成交互式HTML图表，支持：
- 节点拖拽
- 关系查看
- 缩放和平移
- 悬停信息显示

## API参考

### FinancialAgent.execute()

执行知识图谱构建：

```python
def execute(self, init_entity_list: List[str], dump_file_path: str, 
            max_iter: int = 10, search_strategy: str = "mixed") -> Dict
```

### FinancialAgent.query_knowledge_graph()

查询知识图谱：

```python
def query_knowledge_graph(self, query: str) -> List[FinancialRelation]
```

### FinancialAgent.get_entity_relations()

获取特定实体的关系：

```python
def get_entity_relations(self, entity: str) -> List[FinancialRelation]
```

## 使用场景

1. **金融研究**: 自动发现金融市场中的实体关系
2. **投资分析**: 分析投资标的之间的相互影响
3. **风险管理**: 识别风险传导路径
4. **政策分析**: 分析政策对市场的影响机制

## 注意事项

1. **API限制**: 注意搜索API的调用频率限制
2. **数据质量**: 建议对生成的关系进行人工验证
3. **成本控制**: 大模型调用会产生费用，注意控制迭代次数
4. **环境配置**: 确保正确配置API密钥和基础URL

## 贡献

欢迎提交Issue和Pull Request来改进项目！

## 许可证

MIT License 