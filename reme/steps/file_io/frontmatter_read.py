"""``frontmatter_read_step`` — surface a markdown file's frontmatter.

Cheap structured read — frontmatter only, no body. Use ``body:read``
for the post-frontmatter content slice, or whole-file ``read`` when
you want both at once. The answer is textual — ``- key: value`` per
line — because MCP callers only ever see ``answer``; the parsed
mapping itself is returned in ``metadata["frontmatter"]`` (and
``exists: false`` in metadata when the target doesn't exist).

``path`` is a path relative to the workspace.
"""

import json
from pathlib import Path

import frontmatter
import yaml

from ._path import display_path, gate_md, resolve_path
from ..base_step import BaseStep
from ...components import R


def _render_value(value) -> str:
    """Render one frontmatter key or value on a single answer line.

    ``frontmatter_read`` is served straight to the LLM, so the answer has
    to carry the frontmatter itself. Collections keep their JSON shape so
    list boundaries, empty collections, and nested structure stay visible;
    ``default=str`` covers YAML-only types such as dates, and skipping key
    sort keeps mixed-type mapping keys loadable. Bare strings are the one
    exception — quoting every scalar would drown the answer in noise — but
    their line breaks are escaped so the one-key-per-line layout survives.
    """
    if isinstance(value, str):
        return value.replace("\r", "\\r").replace("\n", "\\n")
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError, RecursionError):
        return repr(value)


@R.register("frontmatter_read_step")
class FrontmatterReadStep(BaseStep):
    """Read a Markdown file's frontmatter (YAML metadata only)."""

    async def execute(self):
        assert self.context is not None
        path: str = self.context.get("path") or ""
        assert path, "path is required"

        workspace_dir = Path(self.file_store.workspace_path or ".").resolve()
        target, err = resolve_path(workspace_dir, path)
        if err or target is None:
            self.context.response.success = False
            self.context.response.answer = f"Error: {err or 'invalid path'}"
            self.context.response.metadata.update({"path": path, "exists": False, "error": err or "invalid path"})
            self.logger.info(f"[{self.name}] path={path} error={err!r}")
            return
        original_target = target
        target, is_md = gate_md(target)
        resolved: dict = {}
        if target != original_target:
            resolved["resolved_path"] = display_path(workspace_dir, target)
        probed = resolved.get("resolved_path", path)
        if not target.is_file():
            self.context.response.success = False
            self.context.response.answer = f"Error: {probed} not found"
            self.context.response.metadata.update({"path": path, "exists": False, **resolved})
            self.logger.info(f"[{self.name}] path={path} exists=False")
            return
        if not is_md:
            self.context.response.success = False
            self.context.response.answer = "Error: not markdown"
            self.context.response.metadata.update({"path": path, "error": "not markdown"})
            self.logger.info(f"[{self.name}] path={path} error=not_markdown")
            return

        try:
            meta = dict(frontmatter.loads(target.read_text(encoding="utf-8")).metadata)
        except yaml.YAMLError as exc:
            self.context.response.success = False
            self.context.response.answer = f"Error: failed to parse frontmatter in {probed}: {exc}"
            self.context.response.metadata.update({"path": path, "exists": True, "error": str(exc), **resolved})
            self.logger.info(f"[{self.name}] path={path} parse_error={exc!r}")
            return
        self.context.response.success = True
        header = f"Read frontmatter from {probed} ({len(meta)} key(s))"
        rendered = [f"- {_render_value(key)}: {_render_value(value)}" for key, value in meta.items()]
        self.context.response.answer = f"{header}:\n" + "\n".join(rendered) if rendered else f"{header}: (no keys)"
        self.context.response.metadata.update({"path": path, "exists": True, "frontmatter": meta, **resolved})
        self.logger.info(f"[{self.name}] path={path} keys={len(meta)}")
