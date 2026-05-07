from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Paths:
    eval_root: Path
    repo_root: Path
    skills_root: Path
    runs_root: Path


@dataclass(frozen=True)
class Skill:
    name: str
    path: Path


def discover_paths(repo_root_override: Path | None = None) -> Paths:
    eval_root = Path(__file__).resolve().parents[2]
    repo_root = repo_root_override.resolve() if repo_root_override else eval_root.parent
    return Paths(
        eval_root=eval_root,
        repo_root=repo_root,
        skills_root=repo_root / "skills",
        runs_root=eval_root / "runs",
    )


def discover_skills(skills_root: Path) -> list[Skill]:
    if not skills_root.exists():
        return []
    skills = [
        Skill(name=read_skill_name(skill_file), path=skill_file.parent)
        for skill_file in skills_root.glob("*/SKILL.md")
        if skill_file.is_file()
    ]
    names = [skill.name for skill in skills]
    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    if duplicate_names:
        raise ValueError(f"Duplicate skill name(s): {', '.join(duplicate_names)}")
    return sorted(skills, key=lambda skill: skill.name)


def read_skill_name(skill_file: Path) -> str:
    text = skill_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"Skill file must start with YAML frontmatter: {skill_file}")

    end = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if end is None:
        raise ValueError(f"Skill file has unterminated YAML frontmatter: {skill_file}")

    metadata = yaml.safe_load("\n".join(lines[1:end])) or {}
    if not isinstance(metadata, dict):
        raise ValueError(f"Skill frontmatter must be a mapping: {skill_file}")

    name = metadata.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Skill frontmatter must include a non-empty name: {skill_file}")
    return name.strip()


def resolve_existing_path(path: Path, base: Path) -> Path:
    candidates = [path]
    if not path.is_absolute():
        candidates.append(base / path)
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists():
            return resolved
    raise FileNotFoundError(f"Path does not exist: {path}")


def repo_relative_path(path: Path, paths: Paths) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(paths.repo_root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def unique_run_dir(base: Path) -> Path:
    if not base.exists():
        return base
    for i in range(1, 1000):
        candidate = base.with_name(f"{base.name}-{i:03d}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not allocate run directory for {base}")


def make_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")
