---
name: zama-protocol-dev
description: "Skill routing entry point for Zama Protocol development. Use it to decide which Zama skills to load for a concrete task: use zama-fhevm-solidity-core for contract APIs and Solidity patterns; use zama-hardhat-contract-dev for Hardhat-based contract development, testing, and deployment, usually with core; use zama-foundry-forge-fhevm similarly for Foundry/forge-fhevm; use zama-sdk for TypeScript application code that interacts with Zama contracts; combine SDK with core and either Hardhat or Foundry for a complete dApp; use zama-fhevm-security-review for security review."
---

# Zama Protocol Dev

## Purpose

This skill only selects the right Zama skill or skill combination. It does not provide concrete APIs, code templates, or deployment commands.

Use it when the user has not named a specific Zama skill, or when the task spans contracts, testing frameworks, SDK integration, frontend/backend code, or security review.

## Selection Rules

- Do not load every Zama skill at once.
- First identify the task layer: contract logic, development framework, application integration, full dApp, or security review.
- For a single-layer task, load only the corresponding skill.
- For contract business logic, encrypted types, the `FHE` API, ACL, and decryption design, load `zama-fhevm-solidity-core` first.
- Hardhat and Foundry skills cover project structure, tests, deployment, and local development tooling. Contract-level patterns still belong in core.
- The SDK skill covers TypeScript, React, and Node application code that interacts with deployed or soon-to-be-deployed Zama contracts. A complete dApp also needs core plus one contract framework skill.
- For cross-stack work, load skills in order: core, then Hardhat or Foundry, then SDK. For a complete dApp, read `zama-fullstack-dapp` first to define the overall composition.

## Skill Index

- `zama-fhevm-solidity-core`: Explains FHEVM Solidity APIs and contract-side implementation patterns. Use it for encrypted types, the `FHE` API, encrypted input, ACL, user/public decryption, ERC7984, and contract business logic.
- `zama-hardhat-contract-dev`: Use when the user plans to develop, test, or deploy Zama contracts with Hardhat. Covers `@fhevm/hardhat-plugin`, Hardhat mock, TypeScript tests, tasks, and localhost/Sepolia/mainnet deployment. Usually used together with `zama-fhevm-solidity-core`.
- `zama-foundry-forge-fhevm`: Use when the user plans to develop, test, or deploy Zama contracts with Foundry/forge-fhevm. Covers `FhevmTest`, Forge tests, fuzzing, the local cleartext FHEVM stack, and Foundry deployment. Usually used together with `zama-fhevm-solidity-core`.
- `zama-sdk`: A set of TypeScript libraries for interacting with Zama smart contracts. Use it for browser dApps, React/wagmi/viem/ethers, Node scripts, backend services, relayer runtime, encrypted input, user/public decryption, and ERC7984 token flows. A complete dApp should combine it with `zama-fhevm-solidity-core` and either `zama-hardhat-contract-dev` or `zama-foundry-forge-fhevm`.
- `zama-fullstack-dapp`: Orchestration skill for complete dApps. Use it to decide how contracts, Hardhat/Foundry, the SDK, React/backend code, ABI/address synchronization, runtime selection, and end-to-end validation fit together. It does not replace the concrete skills above.
- `zama-fhevm-security-review`: Use for audits or security reviews of Zama contracts and application integrations. Focuses on FHEVM-specific risks such as ACL, input proofs, public decryption, replay, reorgs, overflow, and mock-vs-production differences.

## Common Task Mapping

- Write, modify, or explain a Zama Solidity contract: `zama-fhevm-solidity-core`
- Look up the `FHE` API, encrypted types, ACL, decryption, or ERC7984 contract patterns: `zama-fhevm-solidity-core`
- Write Hardhat tests, mocks, tasks, deployment scripts, or fix Hardhat configuration: `zama-fhevm-solidity-core` + `zama-hardhat-contract-dev`
- Write Foundry/forge-fhevm tests, fuzz tests, local cleartext stack logic, or deployment scripts: `zama-fhevm-solidity-core` + `zama-foundry-forge-fhevm`
- Write a React page, Node script, or backend service that calls a Zama contract: `zama-fhevm-solidity-core` + `zama-sdk`
- Build a complete dApp with contracts, frontend, SDK integration, deployment artifacts, and e2e validation: `zama-fullstack-dapp` + `zama-fhevm-solidity-core` + one framework skill + `zama-sdk`
- Audit, review, or investigate FHEVM security risks: `zama-fhevm-security-review`, plus core, framework, or SDK skills as needed
- If the user did not choose Hardhat or Foundry: inspect the repository structure first. If the framework still cannot be inferred, start with `zama-fhevm-solidity-core` and choose a framework skill only when needed.

## References

- [references/skill-map.md](references/skill-map.md): Responsibilities and selection rules for each Zama skill.
- [references/workflow-map.md](references/workflow-map.md): Recommended skill loading order for common workflows.
