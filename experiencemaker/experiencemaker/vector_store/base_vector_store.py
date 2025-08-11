import fcntl
import json
from abc import ABC
from pathlib import Path
from typing import List, Iterable

from loguru import logger
from pydantic import BaseModel, Field
from tqdm import tqdm

from experiencemaker.embedding_model.base_embedding_model import BaseEmbeddingModel
from experiencemaker.schema.vector_node import VectorNode


class BaseVectorStore(BaseModel, ABC):
    embedding_model: BaseEmbeddingModel | None = Field(default=None)
    batch_size: int = Field(default=1024)

    @staticmethod
    def _load_from_path(workspace_id: str, path: str | Path, callback_fn=None, **kwargs) -> Iterable[VectorNode]:
        workspace_path = Path(path) / f"{workspace_id}.jsonl"
        if not workspace_path.exists():
            logger.warning(f"workspace_path={workspace_path} is not exists!")
            return

        with workspace_path.open() as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                for line in tqdm(f, desc="load from path"):
                    if line.strip():
                        node_dict = json.loads(line.strip())
                        if callback_fn:
                            node = callback_fn(node_dict)
                        else:
                            node = VectorNode(**node_dict, **kwargs)
                        node.workspace_id = workspace_id
                        yield node

            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    @staticmethod
    def _dump_to_path(nodes: Iterable[VectorNode], workspace_id: str, path: str | Path = "", callback_fn=None,
                      ensure_ascii: bool = False, **kwargs):
        dump_path: Path = Path(path)
        dump_path.mkdir(parents=True, exist_ok=True)
        dump_file = dump_path / f"{workspace_id}.jsonl"

        count = 0
        with dump_file.open("w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                for node in tqdm(nodes, desc="dump to path"):
                    node.workspace_id = workspace_id
                    if callback_fn:
                        node_dict = callback_fn(node)
                    else:
                        node_dict = node.model_dump()
                    assert isinstance(node_dict, dict)
                    f.write(json.dumps(node_dict, ensure_ascii=ensure_ascii, **kwargs))
                    f.write("\n")
                    count += 1

                return {"size": count}
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def exist_workspace(self, workspace_id: str, **kwargs) -> bool:
        raise NotImplementedError

    def delete_workspace(self, workspace_id: str, **kwargs):
        raise NotImplementedError

    def create_workspace(self, workspace_id: str, **kwargs):
        raise NotImplementedError

    def _iter_workspace_nodes(self, workspace_id: str, **kwargs) -> Iterable[VectorNode]:
        raise NotImplementedError

    def dump_workspace(self, workspace_id: str, path: str | Path = "", callback_fn=None, **kwargs):
        if not self.exist_workspace(workspace_id=workspace_id, **kwargs):
            logger.warning(f"workspace_id={workspace_id} is not exist!")
            return {}

        return self._dump_to_path(nodes=self._iter_workspace_nodes(workspace_id=workspace_id, **kwargs),
                                  workspace_id=workspace_id,
                                  path=path,
                                  callback_fn=callback_fn,
                                  **kwargs)

    def load_workspace(self, workspace_id: str, path: str | Path = "", nodes: List[VectorNode] = None, callback_fn=None,
                       **kwargs):
        if self.exist_workspace(workspace_id, **kwargs):
            self.delete_workspace(workspace_id=workspace_id, **kwargs)
            logger.info(f"delete workspace_id={workspace_id}")

        self.create_workspace(workspace_id=workspace_id, **kwargs)

        all_nodes: List[VectorNode] = []
        if nodes:
            all_nodes.extend(nodes)
        for node in self._load_from_path(path=path, workspace_id=workspace_id, callback_fn=callback_fn, **kwargs):
            all_nodes.append(node)
        self.insert(nodes=all_nodes, workspace_id=workspace_id, **kwargs)
        return {"size": len(all_nodes)}

    def copy_workspace(self, src_workspace_id: str, dest_workspace_id: str, **kwargs):
        if not self.exist_workspace(workspace_id=src_workspace_id, **kwargs):
            logger.warning(f"src_workspace_id={src_workspace_id} is not exist!")
            return {}

        if not self.exist_workspace(dest_workspace_id, **kwargs):
            self.create_workspace(workspace_id=dest_workspace_id, **kwargs)

        nodes = []
        node_size = 0
        for node in self._iter_workspace_nodes(workspace_id=src_workspace_id, **kwargs):
            nodes.append(node)
            node_size += 1
            if len(nodes) >= self.batch_size:
                self.insert(nodes=nodes, workspace_id=dest_workspace_id, **kwargs)
                nodes.clear()

        if nodes:
            self.insert(nodes=nodes, workspace_id=dest_workspace_id, **kwargs)
        return {"size": node_size}

    def search(self, query: str, workspace_id: str, top_k: int = 1, **kwargs) -> List[VectorNode]:
        raise NotImplementedError

    def insert(self, nodes: VectorNode | List[VectorNode], workspace_id: str, **kwargs):
        raise NotImplementedError

    def delete(self, node_ids: str | List[str], workspace_id: str, **kwargs):
        raise NotImplementedError

