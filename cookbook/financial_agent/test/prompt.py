
entity_list = [
    "美元债务",
    "美债利率",
    "美元指数",
    "工业金属银、铜、铝",
    "黄金",
    "稳定币",
    "石油",
    "能源",
    "军工",
    "海运",
]



"""
现在初始状态你有以下的实体列表：

美元债务
美债利率
美元指数
工业金属银、铜、铝
黄金
稳定币
石油
能源
军工
海运


你有一个大模型调用的Client
from experiencemaker.model import OpenAICompatibleBaseLLM

你有两个工具：
1. 代码执行工具
from experiencemaker.tool import CodeTool
2. web search工具
from experiencemaker.tool import DashscopeSearchTool

请你根据以上内容，设计一个金融分析师的Agent，并给出Agent的代码。
Agent的任务：
1. 通过不断的搜索，发现多个实体之间的逻辑关系，例如“美债利率高”、“美元债务高”会让美元变弱，从而导致“美元指数”变弱。
2. 同时通过不断的搜索，不断的补充新的实体到**实体列表**。
3. 多跳的实体关系，可以拆成多个单跳的实体关系。

实体关系的schema如下：
{
    "input_entities": ["实体1", "实体2"],
    "output_entities": ["实体3", "实体4"],
    "relation": "正向、负向、中性", 
    "reasoning": "实体1和实体2是通过什么样的逻辑影响到实体3和实体4",
    "source": "来源",
    "confidence": "置信度",
    "timestamp": "时间戳",
}

最后这些schema的list会变成一个jsonl文件，文件名是：
金融知识图谱.jsonl

```python
class FinAgent(object):

    def execute(self, init_entity_list: list[str], dump_file_path: str, max_iter: int = 100):
        # init_entity_list 是初始的实体列表
        # dump_file_path 是最终的jsonl文件路径
        # max_iter 是最大迭代次数

        # 1. 初始化实体列表
        # 2. 读取dump_file_path中历史的金融知识图谱（如果有），加载到内容
        # 2. 迭代搜索，不断更新已有的知识图谱，不断补充新的知识图谱，不断增加新的实体（和已有的语义去重）
        # 3. 迭代到max_iter次，或者没有新的知识图谱可以补充，则停止迭代, 保存到dump_file_path中
        pass
```

帮忙把整个project写一下
"""