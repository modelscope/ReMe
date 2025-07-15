# ExperienceMaker

## 🌟 What is ExperienceMaker?
ExperienceMaker provides agents with robust capabilities for experience generation and reuse. 
By summarizing agents' past trajectories into experiences, it enables these experiences to be applied to subsequent tasks. 
Through the continuous accumulation of experience, agents can keep learning and progressively become more skilled in performing tasks.

### Core Features
- **Experience Generation**: Generate successful or failed experiences by summarizing the agent's historical trajectories.
- **Experience Reuse**: Apply experiences to new tasks by retrieving them from a vector store, helping the agent improve through practice. During RL training, Experience allows the agent to maintain state information, enabling more efficient rollouts.
- **Experience Management**: Provides direct management of experiences, such as loading, dumping, clearing historical experiences, and other flexible database operations.

### Core Advantages
- **Ease of Use**: An HTTP POST interface is provided, allowing one-click startup via the command line. Configuration can be quickly updated using configuration files and command-line arguments.
- **Flexibility**: A rich library of operations is included. By composing atomic ops into pipelines, users can flexibly implement any summarization or retrieval task.
- **Experience Store**: Ready-to-use out of the box — there's no need for you to manually summarize experiences. You can directly leverage existing, comprehensive experience datasets to greatly enhance your agent’s capabilities.


### Framework

💾 VectorStore: MemoryScope is equipped with a vector database (default is *ElasticSearch*) to store all memory fragments recorded in the system.

🔧 Worker Library: MemoryScope atomizes the capabilities of long-term memory into individual workers, including over 20 workers for tasks such as query information filtering, observation extraction, and insight updating.

🛠️ Operation Library: Based on the worker pipeline, it constructs the operations for memory services, realizing key capabilities such as memory retrieval and memory consolidation.

- Memory Retrieval: Upon arrival of a user query, this operation returns the semantically related memory pieces 
and/or those from the corresponding time if the query involves reference to time.
- Memory Consolidation: This operation takes in a batch of user queries and returns important user information
extracted from the queries as consolidated *observations* to be stored in the memory database.
- Reflection and Re-consolidation: At regular intervals, this operation performs reflection upon newly recorded *observations*
to form and update *insights*. Then, memory re-consolidation is performed to ensure contradictions and repetitions
among memory pieces are properly handled.

# install


## quick start



## 💡 Contribute

Contributions are always encouraged!

We highly recommend install pre-commit hooks in this repo before committing pull requests.
These hooks are small house-keeping scripts executed every time you make a git commit,
which will take care of the formatting and linting automatically.
```shell
pip install -e .
```

Please refer to our [Contribution Guide](./docs/contribution.md) for more details.

## 📖 Citation

Reference to cite if you use ExperiperienceMaker in a paper:

```
@software{ExperiperienceMaker,
author = {///},
month = {0715},
title = {{ExperiperienceMaker}},
url = {https://github.com/modelscope/ExperiperienceMaker},
year = {2025}
}
```
