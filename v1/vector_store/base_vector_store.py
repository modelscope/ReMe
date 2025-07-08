import fcntl
import json
from abc import ABC
from pathlib import Path
from typing import List, Iterable

from loguru import logger
from pydantic import BaseModel, Field
from tqdm import tqdm

from v1.embedding_model.base_embedding_model import BaseEmbeddingModel
from v1.schema.vector_node import VectorNode


class BaseVectorStore(BaseModel, ABC):
    embedding_model: BaseEmbeddingModel = Field(default=...)

    @staticmethod
    def _load_from_path(path: str | Path, workspace_id: str, **kwargs) -> Iterable[VectorNode]:
        workspace_path = Path(path) / f"{workspace_id}.jsonl"
        if workspace_path.exists():
            with workspace_path.open() as f:
                fcntl.flock(f, fcntl.LOCK_SH)
                try:
                    for line in tqdm(f, desc="load from path"):
                        if line.strip():
                            yield VectorNode(**json.loads(line.strip(), **kwargs))

                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)

    @staticmethod
    def _dump_to_path(nodes: Iterable[VectorNode], workspace_id: str, path: str | Path = "",
                      ensure_ascii: bool = False, **kwargs):
        dump_path: Path = Path(path)
        dump_path.mkdir(parents=True, exist_ok=True)
        dump_file = dump_path / f"{workspace_id}.jsonl"

        with dump_file.open("w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                for node in tqdm(nodes, desc="dump to path"):
                    f.write(json.dumps(node.model_dump(), ensure_ascii=ensure_ascii, **kwargs))
                    f.write("\n")
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def exist_workspace(self, workspace_id: str, **kwargs) -> bool:
        raise NotImplementedError

    def _delete_workspace(self, workspace_id: str, **kwargs):
        raise NotImplementedError

    def delete_workspace(self, workspace_id: str, **kwargs):
        if self.exist_workspace(workspace_id, **kwargs):
            self._delete_workspace(workspace_id, **kwargs)

    def _create_workspace(self, workspace_id: str, **kwargs):
        raise NotImplementedError

    def create_workspace(self, workspace_id: str, **kwargs):
        if self.exist_workspace(workspace_id, **kwargs):
            logger.warning(f"workspace={workspace_id} exists~")
            return
        self._create_workspace(workspace_id, **kwargs)

    def _iter_workspace_nodes(self, workspace_id: str, max_size: int = 10000, **kwargs) -> Iterable[VectorNode]:
        raise NotImplementedError

    def dump_workspace(self, workspace_id: str, path: str | Path = "", **kwargs):
        self._dump_to_path(nodes=self._iter_workspace_nodes(workspace_id, **kwargs),
                           workspace_id=workspace_id,
                           path=path, **kwargs)

    def load_workspace(self, workspace_id: str, path: str | Path = "", nodes: List[VectorNode] = None, **kwargs):
        self.create_workspace(workspace_id=workspace_id, **kwargs)
        all_nodes: List[VectorNode] = []
        all_nodes.extend(nodes)
        for node in self._load_from_path(path=path, workspace_id=workspace_id, **kwargs):
            all_nodes.append(node)
        self.insert(nodes=all_nodes, workspace_id=workspace_id, **kwargs)

    def retrieve_by_query(self, query: str, workspace_id: str, top_k: int = 1, **kwargs) -> List[VectorNode]:
        raise NotImplementedError

    def insert(self, nodes: VectorNode | List[VectorNode], workspace_id: str, **kwargs):
        raise NotImplementedError

    def update(self, nodes: VectorNode | List[VectorNode], workspace_id: str, **kwargs):
        raise NotImplementedError

    """
    unimportant
    """

    def retrieve_by_id(self, unique_id: str, workspace_id: str = None, **kwargs) -> VectorNode | None:
        raise NotImplementedError

    def exist_id(self, unique_id: str, workspace_id: str = None, **kwargs) -> bool:
        raise NotImplementedError

    def delete_id(self, unique_id: str, workspace_id: str = None, **kwargs):
        raise NotImplementedError
