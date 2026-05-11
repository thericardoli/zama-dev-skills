# Zama Skill Evals

`evals/` contains a lightweight eval runner for measuring how the agent skills in `../skills` help with Zama FHEVM and protocol development tasks.

The runner is managed with `uv` and executes tasks through the OpenAI Codex CLI. Each task can run in two modes:

- `baseline`: run without loading this repository's skills, to observe Codex's base behavior.
- `skills`: copy the selected skills into a temporary `CODEX_HOME/skills` before running Codex, to observe the impact of the skills.

Run artifacts are written to:

```text
runs/<task-id>/(baseline|skills)/<timestamp>/
```

## Directory Layout

```text
evals/
  src/evals/      CLI, runner, task parsing, and path discovery logic
  schema/         JSON Schema for task YAML files
  tasks/          Runnable eval task YAML files
  fixtures/       Initial workspace files or directories for tasks
  runs/           Eval run artifacts; avoid committing generated output
  pyproject.toml  uv/Python package configuration
```

## Prerequisites

First, make sure the OpenAI Codex CLI is installed and available:

```bash
codex --version
```

The first time you enter `evals/`, sync the Python dependencies:

```bash
cd evals
uv sync
```

All commands below are intended to be run from the `evals/` directory.

## Common Commands

List the skills the runner can discover from this repository:

```bash
uv run zama-eval list-skills
```

Create a task template:

```bash
uv run zama-eval new-task my-task-id
```

If the ID is omitted, the runner creates `task-<timestamp>`:

```bash
uv run zama-eval new-task
```

Run a task:

```bash
uv run zama-eval run tasks/my-task-id.yaml
```

`run` prepares the run directory and workspace, then starts a background worker to execute Codex. After the command returns, you can keep using the terminal. Inspect `result.json`, `codex-events.jsonl`, `codex.stderr.log`, and `workspace/` for results.

Useful debugging options:

```bash
uv run zama-eval run tasks/my-task-id.yaml --dry-run
uv run zama-eval run tasks/my-task-id.yaml --codex-command /path/to/codex
uv run zama-eval run tasks/my-task-id.yaml --timestamp 20260511-120000
uv run zama-eval run tasks/my-task-id.yaml --repo-root ..
```

- `--dry-run`: prepare directories, metadata, and workspaces without invoking Codex.
- `--codex-command`: override `codex.command` from the task or the default `codex`.
- `--timestamp`: set the run directory timestamp, which is useful for repeatable local debugging.
- `--repo-root`: override the repository root. This is usually unnecessary.

## Task YAML

Task files live in `tasks/`. Add the schema comment at the top of each file when possible:

```yaml
# yaml-language-server: $schema=../schema/task.schema.json
```

Minimal task:

```yaml
# yaml-language-server: $schema=../schema/task.schema.json
id: my-task-id

prompt: |
  Implement the requested Zama FHEVM project in the current workspace.

codex:
  model: gpt-5.5
  think_level: medium
  fast_mode: true

baseline: true
skills: all
```

Field reference:

- `id`: required stable task ID. Run artifacts are written under `runs/<id>/...`. The ID may contain letters, numbers, dots, underscores, and hyphens, and must start with a letter or number.
- `description`: optional task description. The runner does not currently use it directly.
- `prompt`: required full prompt passed to the Codex CLI.
- `fixture`: optional initial workspace file or directory. Relative paths are resolved from `evals/`.
- `baseline`: optional flag for running the baseline mode. Omitted or `null` is treated as `true`.
- `skills`: optional skill selection for the skills run. Omitted is treated as `all`.
- `codex`: optional Codex CLI configuration.
- `artifacts`: reserved for future artifact collection. It is currently documented and schema-only.

`skills` supports three forms:

```yaml
skills: all
```

```yaml
skills:
  - zama-protocol-dev
  - zama-fhevm-solidity-core
  - zama-sdk
```

```yaml
skills: null
```

- `all`: load every skill discovered from `../skills/*/SKILL.md`.
- list: load only the named skills. Names come from the `name` field in each `SKILL.md` frontmatter.
- `null`: disable the skills run and keep only the baseline run.

If `baseline: false` and `skills: null` are both set, the task has no runnable mode and the runner fails fast.

## Codex Configuration

The `codex` field controls the arguments used for each `codex exec` run:

```yaml
codex:
  command: codex
  model: gpt-5.5
  think_level: medium
  timeout_sec: 1200
  fast_mode: true
  search: false
  args: []
```

- `command`: Codex executable name or path. Defaults to `codex`.
- `model`: model name passed to `codex exec -m`.
- `think_level`: value written to `model_reasoning_effort`. Supported values are `low`, `medium`, `high`, and `xhigh`.
- `timeout_sec`: timeout for each Codex run. Defaults to `1200` seconds.
- `fast_mode`: `true` passes `--enable fast_mode`, `false` passes `--disable fast_mode`, and omitting the field or setting it to `null` leaves the Codex CLI default unchanged.
- `search`: pass `--search` to the Codex CLI.
- `args`: extra raw CLI arguments appended before the prompt stdin marker `-`.

The runner always passes:

```text
codex exec --json --color never --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox -C <workspace> -o <last-message.md>
```

This means Codex can install dependencies, access the network, and execute real development workflows during eval tasks. Only run trusted task YAML and fixture content.

## Fixtures And Workspaces

Use `fixture` to provide an initial workspace for each run:

```yaml
fixture: fixtures/my-project
```

If `fixture` points to a directory, the runner copies the whole directory into the run's `workspace/` and ignores any nested `.git`. If it points to a single file, the runner copies that file into the root of an empty workspace.

Each workspace is initialized with:

```bash
git init
git add -A
git commit --allow-empty -m "initial fixture"
```

After the run finishes, use `git-status.txt` and `diff.patch` to inspect what Codex changed relative to the initial fixture.

## Run Artifacts

A task can produce one or two runs:

```text
runs/<task-id>/baseline/<timestamp>/
runs/<task-id>/skills/<timestamp>/
```

Common files in each run directory:

- `metadata.json`: task, skills, model, and workspace metadata.
- `result.json`: run status, Codex exit code, duration, and timeout information.
- `worker-command.json`: background worker command and PID.
- `worker.log`: runner and worker logs.
- `prompt.md`: prompt passed to Codex.
- `codex-command.json`: actual Codex CLI command.
- `codex-events.jsonl`: raw Codex JSON event stream.
- `codex-events.md`: readable report generated from the event stream, including messages, commands, file changes, and failed command summaries.
- `codex.stderr.log`: Codex stderr.
- `last-message.md`: final Codex message.
- `git-status.txt`: final `git status --short` for the workspace.
- `diff.patch`: binary-safe diff from the initial workspace commit.
- `workspace/`: final workspace.

Common `result.json` statuses:

- `dry_run`: directories were prepared, but Codex was not invoked.
- `queued`: the background worker has started and is waiting to run.
- `running`: Codex is running.
- `completed`: Codex exited successfully.
- `codex_failed`: Codex exited with a non-zero status.
- `codex_timeout`: Codex exceeded `timeout_sec`.
- `runner_failed`: the runner itself failed.

## Development And Validation

Build the eval package:

```bash
uv build
```

After changing runner behavior, run at least one representative task:

```bash
uv run zama-eval run tasks/my-task-id.yaml
```

Artifacts under `runs/` are usually large and may contain local environment details. Avoid committing them.
