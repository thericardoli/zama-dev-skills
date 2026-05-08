from __future__ import annotations

from pathlib import Path

from .paths import Paths, make_timestamp
from .task_config import validate_task_id


def create_task_template(paths: Paths, task_id: str | None = None) -> Path:
    final_id = validate_task_id(task_id or f"task-{make_timestamp()}")
    task_file = paths.eval_root / "tasks" / f"{final_id}.yaml"
    if task_file.exists():
        raise FileExistsError(f"Task file already exists: {task_file}")

    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(render_task_template(final_id), encoding="utf-8")
    return task_file


def render_task_template(task_id: str) -> str:
    return f"""# yaml-language-server: $schema=../schema/task.schema.json
id: {task_id}

prompt: |
  TODO: 写清楚 Codex 需要完成的任务和验收标准。

# fixture 可选。配置后 runner 会先把对应文件或目录复制到每次 run 的 workspace。
# 路径相对 evals/，推荐把初始项目放在 evals/fixtures/<task-id>/。
# 示例：
# fixture: fixtures/{task_id}
# fixture: fixtures/{task_id}/README.md

codex:
  model: gpt-5.5
  think_level: medium
  timeout_sec: 1200
  fast_mode: true

baseline: true
skills: all
"""
