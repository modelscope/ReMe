from flowllm import C
from flowllm.context.flow_context import FlowContext
from flowllm.op.agent.react_v2_op import ReactV2Op


@C.register_op()
class SimpleReactOp(ReactV2Op):
    ...


if __name__ == "__main__":
    from reme_ai.config.config_parser import ConfigParser

    C.set_default_service_config(parser=ConfigParser).init_by_service_config()
    context = FlowContext(query="茅台和五粮现在股价多少？")

    op = SimpleReactOp()
    op(context=context)
    # from reme_ai.schema import Message
    # result = op.llm.chat(messages=[Message(**{"role": "user", "content": "你叫什么名字？"})])
    # print("!!!", result)
