from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .paths import discover_paths, discover_skills, repo_relative_path
from .runner import run_task, run_worker
from .templates import create_task_template


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "worker":
        run_worker_command(argv[1:])
        return

    parser = argparse.ArgumentParser(prog="zama-eval")
    subcommands = parser.add_subparsers(dest="command", required=True)

    add_run_parser(subcommands)
    add_list_skills_parser(subcommands)
    add_new_task_parser(subcommands)

    args = parser.parse_args(argv)
    paths = discover_paths(getattr(args, "repo_root", None))

    if args.command == "list-skills":
        for skill in discover_skills(paths.skills_root):
            print(skill.name)
        return

    if args.command == "new-task":
        if args.id and args.id_option:
            raise SystemExit("Use either positional id or --id, not both.")
        task_file = create_task_template(paths, task_id=args.id_option or args.id)
        print(f"created {repo_relative_path(task_file, paths)}")
        return

    if args.command == "run":
        run_task(
            task_path=args.task,
            paths=paths,
            timestamp=args.timestamp,
            codex_command=args.codex_command,
            dry_run=args.dry_run,
        )
        return

    raise AssertionError(f"Unhandled command: {args.command}")


def run_worker_command(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="zama-eval worker")
    parser.add_argument("run_dir", type=Path)
    add_repo_root_argument(parser)
    args = parser.parse_args(argv)
    paths = discover_paths(args.repo_root)
    run_worker(args.run_dir, paths)


def add_run_parser(subcommands: argparse._SubParsersAction) -> None:
    run_parser = subcommands.add_parser("run", help="Run one task YAML")
    run_parser.add_argument("task", type=Path, help="Path to a task YAML file")
    run_parser.add_argument(
        "--timestamp",
        help="Override run timestamp, useful for deterministic local tests",
    )
    run_parser.add_argument(
        "--codex-command", default=None, help="Override codex executable path"
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prepare run directories but do not invoke Codex",
    )
    add_repo_root_argument(run_parser)


def add_list_skills_parser(subcommands: argparse._SubParsersAction) -> None:
    list_parser = subcommands.add_parser(
        "list-skills", help="List skills discovered under repo skills/"
    )
    add_repo_root_argument(list_parser)


def add_new_task_parser(subcommands: argparse._SubParsersAction) -> None:
    new_task_parser = subcommands.add_parser(
        "new-task", help="Create a task YAML template under evals/tasks/"
    )
    new_task_parser.add_argument(
        "id",
        nargs="?",
        help="Optional task id. Defaults to task-<timestamp>.",
    )
    new_task_parser.add_argument(
        "--id",
        dest="id_option",
        help="Optional task id. Same as the positional id.",
    )
    add_repo_root_argument(new_task_parser)


def add_repo_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--repo-root", type=Path, default=None, help="Override repository root"
    )


if __name__ == "__main__":
    main()
