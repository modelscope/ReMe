import asyncio

from flowllm import C
from flowllm.context.flow_context import FlowContext
from flowllm.op.gallery.react_llm_op import ReactLLMOp


@C.register_op()
class SimpleReactOp(ReactLLMOp):
    ...


async def main():
    from reme_ai.config.config_parser import ConfigParser

    C.set_service_config(parser=ConfigParser, config_name="config=default").init_by_service_config()
    context = FlowContext(query="茅台和五粮现在股价多少？")

    op = SimpleReactOp()
    await op.async_call(context=context)
    print(context.response.answer)

if __name__ == "__main__":
    asyncio.run(main())
