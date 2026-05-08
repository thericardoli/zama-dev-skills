from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from .paths import (
    Paths,
    discover_skills,
    make_timestamp,
    repo_relative_path,
    resolve_existing_path,
    unique_run_dir,
)
from .task_config import build_run_specs, load_task, require_str, validate_task_id

SENSITIVE_CODEX_HOME_ENTRIES = (
    "auth.json",
    "installation_id",
    "sessions",
    "history.jsonl",
    "history.sqlite",
    "log",
    "logs",
    "codex.log",
)

ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
MAX_REPORT_OUTPUT_CHARS = 20_000


def run_task(
    *,
    task_path: Path,
    paths: Paths,
    timestamp: str | None,
    codex_command: str | None,
    dry_run: bool,
) -> None:
    task_file = resolve_existing_path(task_path, paths.eval_root)
    task = load_task(task_file)
    task_id = validate_task_id(require_str(task, "id"))
    prompt = require_str(task, "prompt")
    runs = build_run_specs(task, paths)
    run_timestamp = timestamp or make_timestamp()
    prepared_runs: list[dict[str, Path | str]] = []

    for run_name, selected_skills in runs:
        prepared = prepare_eval_run(
            task=task,
            task_file=task_file,
            task_id=task_id,
            prompt=prompt,
            run_name=run_name,
            selected_skills=selected_skills,
            paths=paths,
            timestamp=run_timestamp,
            codex_command=codex_command,
            dry_run=dry_run,
        )
        prepared_runs.append(prepared)

        if dry_run:
            mark_dry_run(prepared["run_dir"])
        else:
            start_background_worker(Path(prepared["run_dir"]), paths)

    print_run_summary(prepared_runs, paths, dry_run=dry_run)


def prepare_eval_run(
    *,
    task: dict[str, Any],
    task_file: Path,
    task_id: str,
    prompt: str,
    run_name: str,
    selected_skills: list[str],
    paths: Paths,
    timestamp: str,
    codex_command: str | None,
    dry_run: bool,
) -> dict[str, Path | str]:
    run_dir = unique_run_dir(paths.runs_root / task_id / run_name / timestamp)
    workspace = run_dir / "workspace"
    run_dir.mkdir(parents=True, exist_ok=False)

    codex_config = dict(task.get("codex") or {})
    model = codex_config.get("model")
    think_level = codex_config.get("think_level")
    fast_mode = optional_bool(codex_config.get("fast_mode"), "codex.fast_mode")

    prepare_workspace(task, paths, workspace)
    init_git_workspace(workspace)

    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    write_json(
        run_dir / "metadata.json",
        {
            "task_id": task_id,
            "run_name": run_name,
            "task_file": repo_relative_path(task_file, paths),
            "workspace": repo_relative_path(workspace, paths),
            "model": model,
            "think_level": think_level,
            "fast_mode": fast_mode,
            "skills": selected_skills,
            "codex": codex_config,
            "codex_command": codex_command,
            "dry_run": dry_run,
        },
    )

    result: dict[str, Any] = {
        "task_id": task_id,
        "model": model,
        "think_level": think_level,
        "fast_mode": fast_mode,
        "skills": selected_skills,
        "codex_exit_code": None,
        "codex_timed_out": False,
        "status": "prepared",
    }

    write_json(run_dir / "result.json", result)
    return {
        "run_name": run_name,
        "run_dir": run_dir,
        "workspace": workspace,
        "result": run_dir / "result.json",
        "worker_log": run_dir / "worker.log",
    }


def mark_dry_run(run_dir: Path) -> None:
    result = read_json(run_dir / "result.json")
    result["status"] = "dry_run"
    write_json(run_dir / "result.json", result)


def start_background_worker(run_dir: Path, paths: Paths) -> None:
    result = read_json(run_dir / "result.json")
    result["status"] = "queued"
    write_json(run_dir / "result.json", result)

    worker_command = [
        sys.executable,
        "-m",
        "evals.cli",
        "worker",
        str(run_dir),
        "--repo-root",
        str(paths.repo_root),
    ]
    command = ["nohup", *worker_command]
    worker_log = run_dir / "worker.log"
    worker_command_path = run_dir / "worker-command.json"
    write_json(
        worker_command_path,
        {
            "command": command,
            "cwd": str(paths.eval_root),
            "log": repo_relative_path(worker_log, paths),
        },
    )

    with worker_log.open("ab") as log:
        process = subprocess.Popen(
            command,
            cwd=paths.eval_root,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=os.environ.copy(),
            start_new_session=True,
            close_fds=True,
        )

    worker_command = read_json(worker_command_path)
    worker_command["pid"] = process.pid
    write_json(worker_command_path, worker_command)


def run_worker(run_dir: Path, paths: Paths) -> None:
    try:
        complete_prepared_run(run_dir, paths)
    except Exception as exc:
        result_path = run_dir / "result.json"
        if result_path.exists():
            result = read_json(result_path)
        else:
            result = {}
        result["status"] = "runner_failed"
        result["runner_error"] = repr(exc)
        write_json(result_path, result)
        raise


def complete_prepared_run(run_dir: Path, paths: Paths) -> None:
    metadata = read_json(run_dir / "metadata.json")
    task_id = str(metadata["task_id"])
    run_name = str(metadata["run_name"])
    prompt = (run_dir / "prompt.md").read_text(encoding="utf-8")
    raw_selected_skills = metadata.get("skills")
    selected_skills = [str(skill) for skill in raw_selected_skills or []]
    codex_command = metadata.get("codex_command")

    workspace = run_dir / "workspace"
    codex_config = dict(metadata.get("codex") or {})
    model = codex_config.get("model")
    think_level = codex_config.get("think_level")
    fast_mode = optional_bool(codex_config.get("fast_mode"), "codex.fast_mode")
    timeout_sec = int(codex_config.get("timeout_sec", 1200))

    result = read_json(run_dir / "result.json")
    result["status"] = "running"
    write_json(run_dir / "result.json", result)

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="zama-eval-codex-home-") as tmp_home:
        codex_home = Path(tmp_home)
        prepare_codex_home(paths, codex_home, selected_skills)
        try:
            copy_codex_runtime_files(codex_home)
            codex_result = run_codex(
                codex_config=codex_config,
                prompt=prompt,
                workspace=workspace,
                run_dir=run_dir,
                codex_home=codex_home,
                codex_command=codex_command
                or str(codex_config.get("command", "codex")),
                model=model,
                think_level=think_level,
                fast_mode=fast_mode,
                timeout_sec=timeout_sec,
            )
        finally:
            scrub_codex_home(codex_home)

    result["codex_exit_code"] = codex_result["exit_code"]
    result["codex_timed_out"] = codex_result["timed_out"]
    result["codex_duration_sec"] = round(time.monotonic() - started, 3)

    save_git_state(workspace, run_dir)

    events_report = write_codex_events_report(run_dir)
    if events_report is not None:
        result["codex_events_report"] = repo_relative_path(events_report, paths)

    result["status"] = compute_status(result)
    write_json(run_dir / "result.json", result)
    print(f"[{result['status']}] {task_id} / {run_name}: {run_dir}")


def print_run_summary(
    prepared_runs: list[dict[str, Path | str]],
    paths: Paths,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        print("dry-run 已准备以下 eval run：")
    else:
        print("已在后台启动以下 eval run，终端可以关闭或继续使用：")

    for prepared in prepared_runs:
        run_name = str(prepared["run_name"])
        workspace = repo_relative_path(Path(prepared["workspace"]), paths)
        result = repo_relative_path(Path(prepared["result"]), paths)
        worker_log = repo_relative_path(Path(prepared["worker_log"]), paths)
        print(f"- {run_name}")
        print(f"  workspace: {workspace}")
        print(f"  result:    {result}")
        if not dry_run:
            print(f"  log:       {worker_log}")

    if dry_run:
        print("dry-run 不会执行 Codex；确认 metadata.json、result.json 和 workspace 即可。")
    else:
        print("后续查看 result.json、codex-events.md、codex.stderr.log 和 workspace 即可。")


def run_codex(
    *,
    codex_config: dict[str, Any],
    prompt: str,
    workspace: Path,
    run_dir: Path,
    codex_home: Path,
    codex_command: str,
    model: str | None,
    think_level: str | None,
    fast_mode: bool | None,
    timeout_sec: int,
) -> dict[str, Any]:
    output_last_message = run_dir / "last-message.md"
    stdout_path = run_dir / "codex-events.jsonl"
    stderr_path = run_dir / "codex.stderr.log"

    command = [
        codex_command,
        "exec",
        "--json",
        "--color",
        "never",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        str(workspace),
        "-o",
        str(output_last_message),
    ]
    if model:
        command.extend(["-m", str(model)])
    if think_level:
        command.extend(["-c", f'model_reasoning_effort="{think_level}"'])
    if fast_mode is True:
        command.extend(["--enable", "fast_mode"])
    elif fast_mode is False:
        command.extend(["--disable", "fast_mode"])
    if codex_config.get("search"):
        command.append("--search")
    command.extend([str(arg) for arg in (codex_config.get("args") or [])])
    command.append("-")

    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)

    (run_dir / "codex-command.json").write_text(
        json.dumps(
            {"command": command, "cwd": str(workspace), "timeout_sec": timeout_sec},
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            completed = subprocess.run(
                command,
                input=prompt.encode("utf-8"),
                stdout=stdout,
                stderr=stderr,
                cwd=workspace,
                env=env,
                timeout=timeout_sec,
                check=False,
            )
        return {"exit_code": completed.returncode, "timed_out": False}
    except subprocess.TimeoutExpired as exc:
        with stderr_path.open("ab") as stderr:
            stderr.write(f"\n[TIMEOUT] Codex exceeded {timeout_sec}s\n".encode("utf-8"))
            if exc.stderr:
                stderr.write(
                    exc.stderr
                    if isinstance(exc.stderr, bytes)
                    else str(exc.stderr).encode("utf-8")
                )
        return {"exit_code": None, "timed_out": True}


def optional_bool(value: Any, field_path: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise ValueError(f"Task field `{field_path}` must be a boolean or null")


def write_codex_events_report(run_dir: Path) -> Path | None:
    events_path = run_dir / "codex-events.jsonl"
    if not events_path.exists():
        return None

    events, invalid_lines = read_codex_events(events_path)
    report_path = run_dir / "codex-events.md"
    report_path.write_text(
        render_codex_events_report(events, invalid_lines), encoding="utf-8"
    )
    return report_path


def read_codex_events(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    invalid_lines: list[str] = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                invalid_lines.append(f"line {line_number}: {exc.msg}")
                continue
            if isinstance(event, dict):
                events.append(event)
            else:
                invalid_lines.append(f"line {line_number}: expected object")

    return events, invalid_lines


def render_codex_events_report(
    events: list[dict[str, Any]], invalid_lines: list[str]
) -> str:
    timeline = collect_codex_item_timeline(events)
    final_items = [item for _, item in timeline]
    agent_messages = [
        item for item in final_items if item.get("type") == "agent_message"
    ]
    commands = [
        item for item in final_items if item.get("type") == "command_execution"
    ]
    file_changes = [item for item in final_items if item.get("type") == "file_change"]
    failed_commands = [item for item in commands if command_has_problem(item)]

    thread_ids = [
        str(event["thread_id"])
        for event in events
        if event.get("type") == "thread.started" and event.get("thread_id")
    ]
    usage = latest_turn_usage(events)

    lines = [
        "# Codex 事件报告",
        "",
        "## 摘要",
        "",
        f"- 事件数: `{len(events)}`",
        f"- 对话轮次: `{count_events(events, 'turn.started')}`",
        f"- 助手消息: `{len(agent_messages)}`",
        f"- 命令执行: `{len(commands)}`",
        f"- 文件变更: `{len(file_changes)}`",
        f"- 异常命令: `{len(failed_commands)}`",
    ]
    if thread_ids:
        lines.append(f"- Thread ID: `{thread_ids[-1]}`")
    if usage:
        usage_parts = [
            f"{key}: `{value}`" for key, value in usage.items() if value is not None
        ]
        lines.append(f"- Token usage: {', '.join(usage_parts)}")
    if invalid_lines:
        lines.append(f"- 无法解析的 JSONL 行: `{len(invalid_lines)}`")

    if invalid_lines:
        lines.extend(["", "## 解析警告", ""])
        lines.extend(f"- {line}" for line in invalid_lines)

    if failed_commands:
        lines.extend(["", "## 异常命令", ""])
        for command in failed_commands:
            lines.append(
                "- "
                f"status `{command.get('status')}`, "
                f"exit `{command.get('exit_code')}`: "
                f"`{single_line(command.get('command'))}`"
            )

    lines.extend(["", "## 时间线", ""])
    if not timeline:
        lines.append("_没有 item 事件。_")
    for index, (item_id, item) in enumerate(timeline, start=1):
        lines.extend(render_codex_timeline_item(index, item_id, item))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def collect_codex_item_timeline(
    events: list[dict[str, Any]]
) -> list[tuple[str, dict[str, Any]]]:
    items: dict[str, dict[str, dict[str, Any]]] = {}
    order: list[str] = []
    anonymous_count = 0

    for event in events:
        item = event.get("item")
        if not isinstance(item, dict):
            continue

        raw_item_id = item.get("id")
        if raw_item_id is None:
            anonymous_count += 1
            item_id = f"anonymous-{anonymous_count}"
        else:
            item_id = str(raw_item_id)

        if item_id not in items:
            items[item_id] = {}
            order.append(item_id)

        event_type = event.get("type")
        if event_type == "item.started":
            items[item_id]["started"] = item
        elif event_type == "item.completed":
            items[item_id]["completed"] = item
        else:
            items[item_id][str(event_type)] = item

    timeline: list[tuple[str, dict[str, Any]]] = []
    for item_id in order:
        state = items[item_id]
        item = state.get("completed") or state.get("started")
        if item is not None:
            timeline.append((item_id, item))
    return timeline


def render_codex_timeline_item(
    index: int, item_id: str, item: dict[str, Any]
) -> list[str]:
    item_type = str(item.get("type") or "unknown")
    title = {
        "agent_message": "助手消息",
        "command_execution": "命令执行",
        "file_change": "文件变更",
    }.get(item_type, item_type)
    lines = [f"### {index}. {title} `{item_id}`"]

    if item_type == "agent_message":
        text = str(item.get("text") or "").strip()
        lines.extend(["", text or "_空消息_"])
        return lines

    if item_type == "command_execution":
        lines.append(f"- Status: `{item.get('status')}`")
        lines.append(f"- Exit code: `{item.get('exit_code')}`")
        lines.extend(
            ["", "Command:", fenced_block(str(item.get("command") or ""), "bash")]
        )
        output = clean_event_text(item.get("aggregated_output"))
        if output:
            lines.extend(["", "Output:", fenced_block(truncate_text(output), "text")])
        return lines

    if item_type == "file_change":
        lines.append(f"- Status: `{item.get('status')}`")
        changes = item.get("changes")
        if isinstance(changes, list) and changes:
            lines.append("")
            for change in changes:
                if isinstance(change, dict):
                    kind = change.get("kind", "change")
                    path = change.get("path", "")
                    lines.append(f"- `{kind}` {path}")
                else:
                    lines.append(f"- {change}")
        return lines

    lines.extend(
        ["", fenced_block(json.dumps(item, ensure_ascii=False, indent=2), "json")]
    )
    return lines


def count_events(events: list[dict[str, Any]], event_type: str) -> int:
    return sum(1 for event in events if event.get("type") == event_type)


def latest_turn_usage(events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(events):
        usage = event.get("usage")
        if event.get("type") == "turn.completed" and isinstance(usage, dict):
            return usage
    return {}


def command_has_problem(item: dict[str, Any]) -> bool:
    status = item.get("status")
    if status and status != "completed":
        return True
    if "exit_code" in item:
        return item.get("exit_code") != 0
    return False


def clean_event_text(value: Any) -> str:
    if value is None:
        return ""
    return ANSI_ESCAPE_PATTERN.sub("", str(value))


def single_line(value: Any) -> str:
    text = clean_event_text(value).strip()
    return " ".join(text.split())


def truncate_text(text: str, limit: int = MAX_REPORT_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text.rstrip()
    head = limit // 2
    tail = limit - head
    omitted = len(text) - limit
    return (
        text[:head].rstrip()
        + f"\n\n... [truncated {omitted} chars] ...\n\n"
        + text[-tail:].lstrip()
    )


def fenced_block(text: str, language: str) -> str:
    fence = "```"
    while fence in text:
        fence += "`"
    return f"{fence}{language}\n{text.rstrip()}\n{fence}"


def prepare_workspace(task: dict[str, Any], paths: Paths, workspace: Path) -> None:
    fixture = task.get("fixture")
    if fixture:
        fixture_path = resolve_existing_path(Path(str(fixture)), paths.eval_root)
        if fixture_path.is_dir():
            shutil.copytree(
                fixture_path, workspace, ignore=shutil.ignore_patterns(".git")
            )
        else:
            workspace.mkdir(parents=True, exist_ok=False)
            shutil.copy2(fixture_path, workspace / fixture_path.name)
    else:
        workspace.mkdir(parents=True, exist_ok=False)


def prepare_codex_home(
    paths: Paths, codex_home: Path, selected_skills: list[str]
) -> None:
    codex_home.mkdir(parents=True, exist_ok=True)
    source_home = Path(
        os.environ.get("CODEX_HOME", Path.home() / ".codex")
    ).expanduser()
    src = source_home / "version.json"
    if src.exists() and src.is_file():
        shutil.copy2(src, codex_home / "version.json")

    (codex_home / "config.toml").write_text(
        "\n".join(
            [
                "[features]",
                "apps = false",
                "memories = false",
                "",
            ]
        ),
        encoding="utf-8",
    )

    skills_target = codex_home / "skills"
    skills_target.mkdir()
    skill_paths = {skill.name: skill for skill in discover_skills(paths.skills_root)}
    for skill_name in selected_skills:
        shutil.copytree(skill_paths[skill_name].path, skills_target / skill_name)


def copy_codex_runtime_files(codex_home: Path) -> None:
    source_home = Path(
        os.environ.get("CODEX_HOME", Path.home() / ".codex")
    ).expanduser()
    for name in ("auth.json", "installation_id"):
        src = source_home / name
        if src.exists() and src.is_file():
            shutil.copy2(src, codex_home / name)


def scrub_codex_home(codex_home: Path) -> None:
    for name in SENSITIVE_CODEX_HOME_ENTRIES:
        target = codex_home / name
        if not target.exists():
            continue
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()


def init_git_workspace(workspace: Path) -> None:
    run_simple(["git", "init"], cwd=workspace)
    run_simple(["git", "add", "-A"], cwd=workspace)
    run_simple(
        [
            "git",
            "-c",
            "user.name=Zama Eval",
            "-c",
            "user.email=zama-eval@example.invalid",
            "commit",
            "--allow-empty",
            "-m",
            "initial fixture",
        ],
        cwd=workspace,
    )


def save_git_state(workspace: Path, run_dir: Path) -> None:
    run_capture(
        ["git", "status", "--short"],
        cwd=workspace,
        output_path=run_dir / "git-status.txt",
    )
    run_simple(["git", "add", "-N", "."], cwd=workspace, allow_failure=True)
    run_capture(
        ["git", "diff", "--binary", "HEAD"],
        cwd=workspace,
        output_path=run_dir / "diff.patch",
        allow_failure=True,
    )


def compute_status(result: dict[str, Any]) -> str:
    if result.get("codex_timed_out"):
        return "codex_timeout"
    if result.get("codex_exit_code") not in (0,):
        return "codex_failed"
    return "completed"


def write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def run_simple(command: list[str], cwd: Path, allow_failure: bool = False) -> None:
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0 and not allow_failure:
        raise RuntimeError(f"Command failed in {cwd}: {' '.join(command)}")


def run_capture(
    command: list[str], cwd: Path, output_path: Path, allow_failure: bool = False
) -> None:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output_path.write_text(completed.stdout or "", encoding="utf-8")
    if completed.returncode != 0 and not allow_failure:
        raise RuntimeError(f"Command failed in {cwd}: {' '.join(command)}")
