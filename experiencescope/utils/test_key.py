import json
import os

from beyondagent.core.schema.module_loader import ModuleLoader


def load_env_keys():
    if os.path.exists(".env"):
        with open(".env") as f:
            config = json.load(f)
            for k, v in config.items():
                os.environ[k] = v


agent_wrapper_loader = ModuleLoader(
    class_path="beyondagent.core.module.agent_wrapper.naive_agent_wrapper",
    class_name="NaiveAgentWrapper",
    config_path="beyondagent/config/agent_wrapper/naive_agent_wrapper.json")

context_generator_loader = ModuleLoader(
    class_path="beyondagent.core.module.context_generator.simple_context_generator",
    class_name="SimpleContextGenerator",
    config_path="beyondagent/config/context_generator/simple_context_generator.json")

summarizer_loader = ModuleLoader(
    class_path="beyondagent.core.module.summarizer.simple_summarizer",
    class_name="SimpleSummarizer",
    config_path="beyondagent/config/summarizer/simple_summarizer.json")

env_loader = ModuleLoader(
    class_path="beyondagent.core.module.environment.simple_environment",
    class_name="SimpleEnvironment",
    config_path="beyondagent/config/environment/simple_environment.json")