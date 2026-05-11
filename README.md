# Zama Dev Skills

Agent skills for Zama FHEVM and protocol development, plus a lightweight eval runner that uses the OpenAI Codex CLI to assess skill quality.

## Project Structure

```text
skills/   Agent skills; each subdirectory is an installable skill
evals/    Lightweight eval runner for measuring skill quality
```

## Available Skills

| Skill | Purpose |
| --- | --- |
| [zama-protocol-dev](skills/zama-protocol-dev/SKILL.md) | Routes Zama development tasks and decides which specialized skills should be combined. |
| [zama-fhevm-solidity-core](skills/zama-fhevm-solidity-core/SKILL.md) | Contract development with `@fhevm/solidity`, including encrypted types, ACLs, encrypted inputs, and decryption patterns. |
| [zama-hardhat-contract-dev](skills/zama-hardhat-contract-dev/SKILL.md) | Hardhat project setup, testing, deployment, mock mode, Sepolia workflows, and mainnet-oriented guidance. |
| [zama-foundry-forge-fhevm](skills/zama-foundry-forge-fhevm/SKILL.md) | Foundry and `forge-fhevm` project setup, testing, deployment, and fuzzing workflows. |
| [zama-sdk](skills/zama-sdk/SKILL.md) | Integrating TypeScript, React, and Node applications with Zama contracts, including SDK runtime setup, wallet integration, encrypted inputs, decryption, and ERC7984 token flows. |
| [zama-fullstack-dapp](skills/zama-fullstack-dapp/SKILL.md) | End-to-end dApp workflows across contracts, deployment, SDK usage, frontend, backend, and artifact coordination. |
| [zama-fhevm-security-review](skills/zama-fhevm-security-review/SKILL.md) | Security review, threat modeling, and remediation checklists for FHEVM contracts and SDK/frontend integrations. |

## Install with `npx skills`

Install all skills from this repository:

```bash
npx skills add https://github.com/thericardoli/zama-dev-skills
```

Install a single skill:

```bash
npx skills add https://github.com/thericardoli/zama-dev-skills --skill zama-sdk
```

Install multiple skills:

```bash
npx skills add https://github.com/thericardoli/zama-dev-skills \
  --skill zama-fhevm-solidity-core \
  --skill zama-foundry-forge-fhevm \
  --skill zama-sdk
```

## Running Evals

The eval runner lives in `evals/`, is managed with `uv`, and executes tasks through the OpenAI Codex CLI. Before running evals, make sure `codex` is installed and available on your `PATH`:

```bash
codex --version
```

The first time you enter the `evals/` directory, sync the Python dependencies:

```bash
cd evals
uv sync
```

Then run the eval CLI:

```bash
uv run zama-eval list-skills
```

Create a new task template:

```bash
uv run zama-eval new-task my-task-id
```

Run a task:

```bash
uv run zama-eval run tasks/my-task-id.yaml
```

Task YAML files support:

- `baseline: true`: run once without loading this repository's skills.
- `skills: all`: load all skills discovered under `../skills`.
- `skills: [zama-sdk, zama-fhevm-solidity-core]`: load only the named skills.
- `fixture: fixtures/<name>`: provide an initial workspace for each run.
- `codex.model`: set the model name passed to the Codex CLI, for example `gpt-5.5`.
- `codex.think_level`: set the reasoning level. Supported values are `low`, `medium`, `high`, and `xhigh`.
- `codex.fast_mode`: configure Codex fast mode. `true` passes `--enable fast_mode`, `false` passes `--disable fast_mode`, and omitting the field or setting it to `null` leaves the Codex CLI default unchanged.

Example task:

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

Run artifacts are written to:

```text
evals/runs/<task-id>/(baseline|skills)/<timestamp>/
```

Common artifacts include `result.json`, `worker.log`, `prompt.md`, `codex-events.md`, `last-message.md`, `git-status.txt`, `diff.patch`, and the final `workspace/`.

## Upstream Monitoring

Upstream Zama and related package sources are listed in [upstream-sources.yaml](upstream-sources.yaml). The scheduled GitHub Actions workflow in [.github/workflows/check-upstream.yml](.github/workflows/check-upstream.yml) checks them every five days, updates [upstream-state.json](upstream-state.json), and opens an issue when a tracked source changes.

Run the checker manually with:

```bash
python scripts/check_upstream.py \
  --sources upstream-sources.yaml \
  --state upstream-state.json \
  --report /tmp/upstream-report.md \
  --summary /tmp/upstream-summary.json \
  --force
```

## License

This repository is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).
