<table>
  <thead>
    <tr>
      <th width="100">MemoryType</th>
      <th width="200">Import</th>
      <th width="400">Desc</th>
      <th width="400">Note</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td align="center">ReMe.PersonalMemoryService</td>
      <td><code>from reme_ai.service.personal_memory_service import PersonalMemoryService</code></td>
      <td>ReMe's personalized memory service (formerly MemoryScope) empowers you to generate, retrieve, and share customized memories. Leveraging advanced LLM, embedding, and vector store technologies, it builds a comprehensive memory system with intelligent, context- and time-aware memory management—seamlessly enabling you to configure and deploy powerful AI agents.</td>
      <td align="center">https://github.com/modelscope/ReMe Need to configure environment variables: <code>FLOW_EMBEDDING_API_KEY</code>, <code>FLOW_EMBEDDING_BASE_URL</code>, <code>FLOW_LLM_API_KEY</code> and <code>FLOW_LLM_BASE_URL</code></td>
    </tr>
    <tr>
      <td align="center">ReMe.TaskMemoryService</td>
      <td><code>from reme_ai.service.task_memory_service import TaskMemoryService</code></td>
      <td>ReMe's task-oriented memory service helps you efficiently manage and schedule task-related memories, enhancing both the accuracy and efficiency of task execution. Powered by LLM capabilities, it supports flexible creation, retrieval, update, and deletion of memories across diverse task scenarios—enabling you to effortlessly build and scale robust agent-based task systems.</td>
      <td>the same as <code>ReMe.PersonalMemoryService</code></td>
    </tr>
  </tbody>
</table>
