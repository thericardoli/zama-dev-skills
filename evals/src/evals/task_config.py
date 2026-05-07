from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .paths import Paths, discover_skills

BASELINE_RUN = "baseline"
SKILLS_RUN = "skills"
TASK_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


def load_task(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Task YAML must contain a mapping: {path}")
    return data


def require_str(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Task field `{key}` must be a non-empty string")
    return value


def validate_task_id(task_id: str) -> str:
    if not TASK_ID_PATTERN.fullmatch(task_id):
        raise ValueError(
            "Task id must match ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ "
            f"(got `{task_id}`)"
        )
    return task_id


def build_run_specs(task: dict[str, Any], paths: Paths) -> list[tuple[str, list[str]]]:
    all_skill_names = [skill.name for skill in discover_skills(paths.skills_root)]

    baseline_value = task.get("baseline", True)
    if baseline_value is None:
        baseline_enabled = True
    elif isinstance(baseline_value, bool):
        baseline_enabled = baseline_value
    else:
        raise ValueError("Task field `baseline` must be a boolean or null")

    skills_value = task.get("skills", "all")
    selected_skills = normalize_skills(skills_value, all_skill_names)

    runs: list[tuple[str, list[str]]] = []
    if baseline_enabled:
        runs.append((BASELINE_RUN, []))
    if selected_skills is not None:
        runs.append((SKILLS_RUN, selected_skills))
    if not runs:
        raise ValueError(
            "Task config disables both runs. Use `baseline: true` or provide `skills`."
        )
    return runs


def normalize_skills(value: Any, all_skill_names: list[str]) -> list[str] | None:
    if isinstance(value, str):
        if value == "all":
            return list(all_skill_names)
        raise ValueError(
            f"Task field `skills` has invalid string `{value}`. "
            "Use `all`, a list of skill names, or null."
        )
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("Task field `skills` must be a list, `all`, or null")
    if not value:
        raise ValueError(
            "Task field `skills` list must contain at least one skill name. "
            "Use `skills: null` to disable the skills run."
        )

    known = set(all_skill_names)
    normalized: list[str] = []
    for skill in value:
        skill_name = str(skill)
        if skill_name not in known:
            raise ValueError(
                f"Task field `skills` references unknown skill `{skill_name}`. "
                f"Known skills: {', '.join(all_skill_names)}"
            )
        if skill_name not in normalized:
            normalized.append(skill_name)
    return normalized
