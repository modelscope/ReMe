from concurrent.futures import as_completed
from itertools import zip_longest
from typing import List

from loguru import logger

from v1.op import OP_REGISTRY
from v1.op.base_op import BaseOp
from v1.pipeline.pipeline_context import PipelineContext
from v1.utils.timer import Timer, timer


class Pipeline:
    seq_symbol: str = "->"
    parallel_symbol: str = "|"

    def __init__(self, pipeline: str, context: PipelineContext):
        self.pipeline_list: List[str | List[str]] = self._parse_pipline(pipeline)
        self.context: PipelineContext = context

    def _parse_pipline(self, pipeline: str) -> List[str | List[str]]:
        pipeline_list: List[str | List[str]] = []

        for pipeline_split1 in pipeline.split("["):
            for sub_pipeline in pipeline_split1.split("]"):
                sub_pipeline = sub_pipeline.strip().strip(self.seq_symbol)
                if not sub_pipeline:
                    continue

                if self.parallel_symbol in sub_pipeline:
                    self.pipeline_list.append(sub_pipeline.split(self.parallel_symbol))
                else:
                    self.pipeline_list.append(sub_pipeline)

        return pipeline_list

    def _execute_sub_pipeline(self, pipeline: str):
        op_config_dict = self.context.app_config.op
        for op in pipeline.split(self.seq_symbol):
            op = op.strip()
            if not op:
                continue

            assert op in op_config_dict, f"op={op} config is missing!"
            backend = op_config_dict[op].backend
            assert backend in OP_REGISTRY, f"op={op} backend={backend} is not registered!"

            op_cls = OP_REGISTRY[backend]
            op_obj: BaseOp = op_cls(context=self.context, **op_config_dict[op].params)
            op_obj.execute_wrap()

    def _parse_sub_pipeline(self, pipeline: str):
        for op in pipeline.split(self.seq_symbol):
            op = op.strip()
            if not op:
                continue

            yield op

    def print_pipeline(self):
        i: int = 0
        for pipeline in self.pipeline_list:
            if isinstance(pipeline, str):
                for op in self._parse_sub_pipeline(pipeline):
                    i += 1
                    logger.info(f"stage_{i}: {op}")

            elif isinstance(pipeline, list):
                parallel_pipeline = [self._parse_sub_pipeline(x) for x in pipeline]
                for op_list in zip_longest(*parallel_pipeline, fillvalue="-"):
                    i += 1
                    logger.info(f"stage{i}: {' | '.join(op_list)}")

            else:
                raise ValueError(f"unknown pipeline.type={type(pipeline)}")

    @timer()
    def __call__(self, enable_print: bool = True):
        if enable_print:
            self.print_pipeline()

        for i, pipeline in enumerate(self.pipeline_list):
            with Timer(f"step_{i}"):
                if isinstance(pipeline, str):
                    self._execute_sub_pipeline(pipeline)

                else:
                    future_list = []
                    for sub_pipeline in pipeline:
                        future = self.context.thread_pool.submit(self._execute_sub_pipeline, pipeline=sub_pipeline)
                        future_list.append(future)

                    for future in as_completed(future_list):
                        future.result()
