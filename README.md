# ReMe.ai

<p align="center">
 <img src="doc/figure/logo.jpg" alt="ReMe.ai Logo" width="100%">
</p>

<p align="center">
  <a href="https://pypi.org/project/reme-ai/"><img src="https://img.shields.io/badge/python-3.12+-blue" alt="Python Version"></a>
  <a href="https://pypi.org/project/reme-ai/"><img src="https://img.shields.io/badge/pypi-v1.0.0-blue?logo=pypi" alt="PyPI Version"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-black" alt="License"></a>
  <a href="https://github.com/modelscope/ReMe.ai"><img src="https://img.shields.io/github/stars/modelscope/ReMe.ai?style=social" alt="GitHub Stars"></a>
</p>

<p align="center">
  <strong>记忆驱动的AI智能体框架</strong><br>
  <em>"如果说我比别人看得更远些，那是因为我站在了巨人的肩膀上。" —— 牛顿</em>
</p>

---

Remember Everyone, Recreate Everything

Remember Me, Reshape Me

Remember Me, Refine Me

Remember Me, Reinvent Me

今天的每个AI智能体都在从零开始。每当智能体处理任务时，它都在重新发明无数其他智能体已经发现的解决方案。这就像要求每个人都从头发现火、农业和数学一样。

ReMe.ai希望改变这一点。我们为AI智能体提供了统一的记忆与经验系统——在跨用户、跨任务、跨智能体下抽取、复用和分享记忆的能力。

```
任务经验 (Task Memory) + 个人记忆 (Personal Memory) = agent的记忆管理
```

个人记忆回答"**如何理解用户需要**"，任务记忆回答"**如何做得更好**"，

---

## 📰 最新动态
- **[2025-09]** 🎉 ReMe.ai v1.0.0 正式发布，整合任务经验与个人记忆
- **[2025-08]** 🚀 MCP协议支持已上线！→ [快速开始指南](./doc/mcp_quick_start.md)
- **[2025-07]** 📚 完整文档和快速开始指南发布
- **[2025-06]** 🚀 多后端向量存储支持 (Elasticsearch & ChromaDB)

---

## ✨ 架构设计

### 🎯 双模记忆系统

ReMe.ai整合两种互补的记忆能力：

#### 🧠 **任务经验 (Task Memory/Experience)**
跨智能体复用的程序性知识
- **成功模式识别**：识别有效策略并理解其根本原理
- **失败分析学习**：从错误中学习，避免重复同样的问题
- **规划策略**：不同问题类型的规划策略
- **工具使用模式**：经过验证的有效工具使用方法
- **标准操作流程**：经过验证的方法论和流程

你可以从[快速开始指南](./doc/task_memory_readme.md)了解更多如何使用task memory的方法

#### 👤 **个人记忆 (personal memory)**
特定用户的情境化记忆
- **个体偏好**：用户的习惯、偏好和交互风格
- **情境适应**：基于时间和上下文的智能记忆管理
- **渐进学习**：通过长期交互逐步建立深度理解
- **时间感知**：检索和整合时都具备时间敏感性

- 你可以从[快速开始指南](./doc/personal_memory_readme.md)了解更多如何使用personal memory的方法


---

## 🛠️ 安装

### 从PyPI安装（推荐）
```bash
pip install reme-ai
```

### 从源码安装
```bash
git clone https://github.com/modelscope/ReMe.ai.git
cd ReMe.ai
pip install .
```

### 环境配置
创建`.env`文件：
```bash
# 必需：LLM API配置
LLM_API_KEY="sk-xxx"
LLM_BASE_URL="https://xxx.com/v1"

# 必需：嵌入模型配置  
EMBEDDING_MODEL_API_KEY="sk-xxx"
EMBEDDING_MODEL_BASE_URL="https://xxx.com/v1"
```

---

## 🚀 快速开始

### HTTP服务启动
```bash
reme \
  backend=http \ 
  http.port=8001 \
  llm.default.model_name=qwen3-30b-a3b-thinking-2507 \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local
```

### MCP服务器支持
```bash
reme \
  backend=mcp \
  mcp.transport=stdio \
  llm.default.model_name=qwen3-30b-a3b-thinking-2507 \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local
```

### 核心API使用

#### 任务经验管理
```python
import requests

# 经验总结器：从执行轨迹学习
response = requests.post("http://localhost:8002/summary_task_memory", json={
    "workspace_id": "task_workspace",
    "trajectories": [
        {"messages": [{"role": "user", "content": "帮我制定项目计划"}], "score": 1.0}
    ]
})

# 经验检索器：获取相关经验
response = requests.post("http://localhost:8002/retrieve_task_memory", json={
    "workspace_id": "task_workspace",
    "query": "如何高效管理项目进度？",
    "top_k": 1
})
```

#### 个人记忆管理  
```python
# 记忆整合：从用户交互中学习
response = requests.post("http://localhost:8002/summary_personal_memory", json={
    "workspace_id": "task_workspace",
    "trajectories": [
        {"messages":
            [
                {"role": "user", "content": "我喜欢早上喝咖啡工作"},
                {"role": "assistant", "content": "了解，您习惯早上用咖啡提神来开始工作"}
            ]
        }
    ]
})

# 记忆检索：获取个人记忆片段
response = requests.post("http://localhost:8002/retrieve_personal_memory", json={
    "workspace_id": "task_workspace",
    "query": "用户的工作习惯是什么？",
    "top_k": 5
})
```

---

## 🧪 实验结果

### Appworld基准测试
使用qwen3-8b在Appworld上的测试结果：

| 方法                         | pass@1    | pass@2      | pass@4    |
|----------------------------|-----------|-------------|-----------|
| 无记忆（基线）               | 0.083     | 0.140       | 0.228     |
| **使用任务经验**            | **0.109** | **0.175**   | **0.281** |

详见：[quickstart.md](cookbook/appworld/quickstart.md)

### FrozenLake实验
使用qwen3-8b在100个随机FrozenLake地图上测试：

| 方法                        | 通过率           | 
|---------------------------|-----------------|
| 无记忆（基线）              | 0.66            | 
| **使用任务经验**           | 0.72 **(+9.1%)** |

|                            无经验                            |                  有经验                   |
|:----------------------------------------------------------:|:---------------------------------------:|
| <p align="center"><img src="doc/figure/frozenlake_failure.gif" alt="失败案例" width="30%"></p> | <p align="center"><img src="doc/figure/frozenlake_success.gif" alt="成功案例" width="30%"></p>

详见：[quickstart.md](cookbook/frozenlake/quickstart.md)

---

## 📦 即用型经验库

ReMe.ai提供预构建的经验库，智能体可以立即使用经过验证的最佳实践：

### 可用经验库
- **`appworld_v1.jsonl`**：Appworld智能体交互的记忆库，涵盖复杂任务规划和执行模式
- **`bfcl_v1.jsonl`**：BFCL工具调用的工作记忆库

### 快速使用
```python
# 加载预构建经验
response = requests.post("http://localhost:8002/vector_store", json={
    "workspace_id": "appworld_v1", 
    "action": "load",
    "path": "./library/"
})

# 查询相关经验
response = requests.post("http://localhost:8002/retrieve_task_memory", json={
    "workspace_id": "appworld_v1",
    "query": "如何导航到设置并更新用户资料？",
    "top_k": 1
})
```

## 📚 相关资源

- **[快速开始](./cookbook/simple_demo/quick_start.md)**：通过实际示例快速上手
- **[向量存储设置](./doc/vector_store_setup.md)**：生产部署指南  
- **[配置指南](./doc/configuration_guide.md)**：详细配置参考
- **[操作文档](./doc/operations_documentation.md)**：操作配置说明
- **[示例集合](./cookbook)**：实际用例和最佳实践

---

## 🤝 贡献

我们相信最好的记忆系统来自集体智慧。欢迎贡献：

### 代码贡献
- 新操作和工具开发
- 后端实现和优化
- API增强和新端点

### 文档改进
- 使用示例和教程
- 最佳实践指南
- 翻译和本地化

---

## 📄 引用

```bibtex
@software{ReMe2025,
  title = {ReMe.ai: Memory-Driven AI Agent Framework},
  author = {The ReMe.ai Team},
  url = {https://github.com/modelscope/ReMe.ai},
  year = {2025}
}
```

---

## ⚖️ 许可证

本项目采用Apache License 2.0许可证 - 详情请参阅[LICENSE](./LICENSE)文件。

---