from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import zip_longest
from typing import Dict, List

from loguru import logger

from v1.op.base_op import BaseOp
from v1.pipeline.pipeline_context import PipelineContext
from v1.utils.timer import Timer, timer


class Pipeline(object):
    seq_symbol: str = "->"
    parallel_symbol: str = "|"

    def __init__(self,
                 name: str,
                 pipeline: str,
                 op_config_dict: Dict[str, dict],
                 op_registry: Dict[str, type[BaseOp]],
                 context: PipelineContext,
                 thread_pool: ThreadPoolExecutor):

        self.name: str = name
        self.pipeline_list: List[str | List[str]] = self._parse_pipline(pipeline)
        self.op_config_dict: Dict[str, dict] = op_config_dict
        self.op_registry: Dict[str, type[BaseOp]] = op_registry
        self.context: PipelineContext = context
        self.thread_pool: ThreadPoolExecutor = thread_pool

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

    def execute_sub_pipeline(self, pipeline: str, context: PipelineContext):
        for op in pipeline.split(self.seq_symbol):
            op = op.strip()
            if not op:
                continue

            assert op in self.op_config_dict, f"op({op}).config is missing!"
            backend = self.op_config_dict.pop("backend", "")
            assert backend in self.op_registry, f"op({op}).backend({backend}) is not registered!"

            op_cls = self.op_registry[backend]
            op_obj: BaseOp = op_cls(**self.op_config_dict[op])
            op_obj.execute_wrap(context)

    def parse_sub_pipeline(self, pipeline: str):
        for op in pipeline.split(self.seq_symbol):
            op = op.strip()
            if not op:
                continue

            yield op

    @timer()
    def print_pipeline(self):
        i: int = 0
        for pipeline in self.pipeline_list:
            if isinstance(pipeline, str):
                for op in self.parse_sub_pipeline(pipeline):
                    i += 1
                    logger.info(f"stage_{i}: {op}")

            elif isinstance(pipeline, list):
                for op_list in zip_longest(*[self.parse_sub_pipeline(x) for x in pipeline], fillvalue="-"):
                    i += 1
                    logger.info(f"stage{i}: {' | '.join(op_list)}")

            else:
                raise ValueError(f"unknown pipeline.type={type(pipeline)}")

    @timer()
    def execute_pipeline(self):
        for i, pipeline in enumerate(self.pipeline_list):
            with Timer(f"step_{i}"):
                if isinstance(pipeline, str):
                    self.execute_sub_pipeline(pipeline, self.context)

                else:
                    future_list = []
                    for sub_pipeline in pipeline:
                        future = self.thread_pool.submit(self.execute_sub_pipeline,
                                                         pipeline=sub_pipeline,
                                                         context=self.context)
                        future_list.append(future)

                    for future in as_completed(future_list):
                        future.result()
