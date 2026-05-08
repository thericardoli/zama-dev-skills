# Zama Codex Evals

This is a small `uv` managed Python project for running Codex CLI eval tasks against the Zama skills in this repository.

Each task declares the runs it wants:

- `baseline`: when `true`, run once with no repo skills copied into `CODEX_HOME`
- `skills`: run once with the declared skill set copied into `CODEX_HOME/skills`

Run outputs are written to:

```text
runs/<task-id>/(baseline|skills)/<timestamp>/
```

## Task YAML

Task files can opt into the local JSON Schema:

```yaml
# yaml-language-server: $schema=../schema/task.schema.json
```

`../schema/schema.json` is also provided as a stable alias. The repository also includes `.vscode/settings.json` so YAML language server can bind `evals/tasks/**/*.yaml` to the task schema even when an individual task omits the comment.

Minimal task:

```yaml
# yaml-language-server: $schema=../schema/task.schema.json
id: example-empty

prompt: |
  Create a short NOTES.md file.

codex:
  model: gpt-5.5
  think_level: medium
  fast_mode: true

baseline: true
skills: all
```

Optional fields:

```yaml
fixture: fixtures/my-project

codex:
  command: codex
  model: gpt-5.5
  think_level: medium
  timeout_sec: 1200
  fast_mode: true
  search: false
  args: []

baseline: true
skills:
  - zama-protocol-dev
  - zama-fhevm-solidity-core
  - zama-foundry-forge-fhevm
  - zama-sdk
```

`fixture`, `baseline`, and `skills` are optional. If no fixture is provided, the runner creates an empty workspace. If `baseline` is omitted, it defaults to `true`. If `skills` is omitted, it defaults to `all`.

The runner starts Codex with `--dangerously-bypass-approvals-and-sandbox` for every task so agents can install dependencies, clone repositories, and access the network during eval runs.

Set `codex.fast_mode` to `true` to pass `--enable fast_mode`, or `false` to pass `--disable fast_mode`. Omit it or set it to `null` to leave the Codex CLI default unchanged.

`skills` accepts:

- a list of skill names read from each `../skills/*/SKILL.md` frontmatter `name`
- `all`: every skill discovered under `../skills`
- `null`: disable the skills run

## Usage

```bash
uv run zama-eval list-skills
uv run zama-eval new-task
uv run zama-eval new-task my-foundry-counter
uv run zama-eval new-task --id my-foundry-counter
uv run zama-eval run tasks/example-empty.yaml
uv run zama-eval run tasks/example-skills.yaml
```

`new-task` writes a template to `tasks/<id>.yaml`. If `id` is omitted, the runner uses `task-<timestamp>`.

`run` starts eval work in the background, prints each run workspace/result path, and returns control to the terminal.

The runner stores:

- `metadata.json`
- `result.json`
- `worker-command.json`
- `worker.log`
- `prompt.md`
- `codex-command.json`
- `codex-events.jsonl`
- `codex-events.md`
- `codex.stderr.log`
- `last-message.md`
- `git-status.txt`
- `diff.patch`
- final `workspace/`

The runner uses an isolated temporary `CODEX_HOME` while Codex is executing, but does not keep that directory in the run artifacts. `codex-events.md` is generated from `codex-events.jsonl` after the run finishes so the event stream can be inspected without reading raw JSONL.
