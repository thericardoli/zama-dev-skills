---
name: zama-fullstack-dapp
description: Use when orchestrating a complete Zama FHEVM dApp across Solidity contracts, Hardhat or Foundry, local development chains, Sepolia/mainnet deployment, @zama-fhe/sdk or @zama-fhe/react-sdk, React/Node clients, ABI/address artifacts, monorepo structure, and end-to-end validation.
---

# Zama Fullstack dApp

This skill is the orchestration layer for complete dApps. It does not provide concrete API examples, and it does not replace framework-specific skills. Its role is to tell the agent where to find the right material and how to connect contracts, deployment, SDK usage, frontend code, and optional backend services.

## When to Use

Use this skill when a task spans two or more layers:

- FHEVM Solidity contract plus frontend
- Contract deployment plus SDK calls
- Dual-network local/Sepolia dApp
- React/Node client-side encrypted input and decryption
- ABI/address artifact synchronization
- Monorepo templates, README files, and end-to-end validation

If the task is only to write a single contract function, a single test, or a single SDK call, do not use this skill. Use the corresponding focused skill directly.

## Overall Loading Order

1. Read this file first to establish layer boundaries and the work sequence.
2. Identify the contract framework:
   - Foundry/Forge: read `references/foundry/README.md`.
   - Hardhat: read `references/hardhat/README.md`.
3. For contract business logic, encrypted types, ACL, and decryption design, read `zama-fhevm-solidity-core`.
4. For the contract framework, tests, and deployment:
   - Foundry: read `zama-foundry-forge-fhevm`.
   - Hardhat: read `zama-hardhat-contract-dev`.
5. For frontend, Node, relayer runtime, signer, storage, encrypted input, and user/public decrypt flows, read `zama-sdk`.
6. For security, ACL, public decrypt, replay protection, and mock-vs-production differences, read `zama-fhevm-security-review`.

If the user has not specified a framework, inspect the repository structure first. In an empty project, prioritize the user's preference. If there is no preference, Foundry is a better fit for Forge-oriented, local cleartext, and quick end-to-end templates; Hardhat is a better fit for TypeScript-first workflows, Hardhat Deploy, TypeChain, and task-based automation.

## Recommended Monorepo Boundaries

Use a consistent `packages` layout:

```text
packages/
├── contract/   # Contracts, contract tests, deployment scripts, contract artifacts
├── frontend/   # React/Vite/Next frontend
└── service/    # Optional: relayer proxy, server jobs, Node SDK smoke tests
```

Responsibility boundaries:

- `packages/contract` is the canonical source for ABI/address artifacts.
- `packages/frontend` only consumes ABI/address artifacts. It should not become the sole source of deployment addresses.
- `packages/service` is added only when the app needs a backend proxy, server-side decrypt flow, public decrypt finalization job, scheduled job, or private relayer credentials.
- Root scripts should only orchestrate commands and delegate concrete work to the relevant package.

## Integration Sequence

1. Contract design
   Use `zama-fhevm-solidity-core` first to define encrypted inputs, handle lifecycles, ACL, user/public decrypt flows, and arithmetic boundaries.

2. Framework implementation
   Use the Foundry or Hardhat skill to build `packages/contract`, including dependencies, tests, deployment scripts, and local/testnet configuration.

3. Artifact design
   Deployment scripts should write ABI and address data to `packages/contract/deployments/`, then generate or copy frontend-consumable files into `packages/frontend/src/contracts/`. Addresses must be separated by chain ID; never keep only "the latest deployment".

4. SDK runtime selection
   Use `zama-sdk` to choose the runtime environment:
   - Browser/frontend: `RelayerWeb`
   - Node/service: `RelayerNode`
   - Local cleartext demo: `RelayerCleartext`

5. Frontend or Node contract integration
   Use the `zama-sdk` custom-contracts, React/wagmi, and Node/local references to design this flow: encrypt input -> submit transaction -> read handle -> authorize decrypt -> user/public decrypt.

6. Optional backend
   Create `packages/service` only when the app needs to hide a relayer API key, provide a proxy, run public decrypt finalization, listen to on-chain events in the background, or execute server-side smoke tests.

7. Validation and README
   The README must clearly document install, local, Sepolia, frontend, service, test/build, and required secrets. Do not stop at "configure env and run".

## Critical Integration Points

- The `contractAddress` passed to `sdk.relayer.encrypt` must be the address of the contract that actually calls `FHE.fromExternal`.
- Handles and input proofs must come from the same encryption operation.
- During decrypt flows, each handle must be paired with the contract address that owns that handle.
- User decrypt requires an explicit authorization action or gate. Do not trigger wallet signatures automatically during render.
- When the account or chain changes, clear stale handles, decrypted values, and session assumptions.
- Local, Sepolia, and mainnet address artifacts must be separated by chain ID.
- `.env` files are not loaded automatically by npm/pnpm scripts; deployment commands need a wrapper or an explicit source step.
- Browsers must not receive private relayer API keys. If a key is required, route through a `packages/service` proxy.
- A successful mock/local cleartext flow does not prove that production user decrypt will work.

## Acceptance Criteria

Before completing a full dApp task, check at least the following:

- Contract compilation.
- Contract tests cover the success path and ACL/proof failure paths.
- Frontend typecheck and production build.
- At least one frontend interaction or state-flow test that is not merely a pure utility test. If this is not feasible, document the gap.
- The local deployment path is executable or clearly documented.
- Sepolia deployment commands fail early with clear messages when RPC, account, or keystore configuration is missing.
- When feasible, run an SDK smoke path: encrypt input, submit transaction, read handle, and decrypt result.
