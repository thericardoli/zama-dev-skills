# Zama Skill Map

## `zama-fhevm-solidity-core`

Responsibilities:

- Explain the contract-side model of Zama Protocol and fhevm-solidity.
- Look up encrypted types and the `FHE` API.
- Design Solidity contract patterns for encrypted input, operations, ACL, decryption, ERC7984, and related FHEVM flows.

## `zama-hardhat-contract-dev`

Responsibilities:

- Hardhat project structure, dependencies, and configuration.
- `@fhevm/hardhat-plugin`.
- Encrypted input and decryption helpers in TypeScript tests.
- Hardhat deployment, localhost, Sepolia, and tasks.

## `zama-foundry-forge-fhevm`

Responsibilities:

- Foundry project configuration.
- `forge-fhevm` and `FhevmTest`.
- Forge tests, fuzz tests, and the local cleartext stack.
- Foundry deployment scripts.

## `zama-fullstack-dapp`

Responsibilities:

- Orchestrate repository structure, runtime selection, and contract/SDK/relayer/frontend boundaries for a complete Zama dApp.
- Define how the Foundry or Hardhat contract-development skill should be combined with `zama-sdk`.
- Distinguish Foundry local cleartext SDK e2e, Hardhat mock flows, local mock-only demos, and testnet/production SDK flows.
- Specify ABI/address synchronization, README requirements, type checks, SDK static checks, and end-to-end validation.

## `zama-sdk`

Responsibilities:

- `@zama-fhe/sdk` and `@zama-fhe/react-sdk`.
- Browser, Node, and local cleartext relayer runtimes.
- React, Next.js, wagmi, viem, and ethers integration for frontends and scripts.
- Encrypted input generation, user decryption, public decryption, and delegated decryption.
- ERC7984 confidential tokens, wrapper registry, and token hooks.
- Sepolia, mainnet, and local relayer configuration.
- The unified replacement for older relayer/react-wagmi skills.

## `zama-fhevm-security-review`

Responsibilities:

- Security review for FHEVM contracts and frontend integrations.
- ACL, proofs, public decryption, replay, and reorg risks.
- Overflow/underflow and encrypted-condition fail-open risks.
- Differences between mock and production environments.

## Selection Rules

- Contract only: core.
- Hardhat development, deployment, or testing: core + hardhat.
- Foundry development, deployment, or testing: core + foundry.
- Contract + React or a complete dApp: `zama-fullstack-dapp` + core + framework skill + `zama-sdk`.
- Scripts or CLI tools: core + `zama-sdk`.
- Security review: security, plus core or framework skills when needed.
