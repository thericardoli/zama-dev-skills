# Hardhat Orchestration Path

When `packages/contract` uses Hardhat plus `@fhevm/hardhat-plugin`, use this file to compose the relevant skills.

## Recommended Structure

```text
packages/
├── contract/
│   ├── contracts/
│   ├── test/
│   ├── deploy/
│   ├── tasks/
│   ├── scripts/
│   ├── deployments/
│   ├── hardhat.config.ts
│   └── package.json
├── frontend/
│   └── src/
└── service/       # Optional
```

## Skills and References to Read

Contract logic:

- `zama-fhevm-solidity-core/SKILL.md`
- For APIs, read `zama-fhevm-solidity-core/references/api.md`
- For protocol and architecture context, read `zama-fhevm-solidity-core/references/overview.md`

Hardhat project and tests:

- `zama-hardhat-contract-dev/SKILL.md`
- To create or fix configuration: `references/hardhat-project.md`
- To deploy locally or to Sepolia: `references/deploy.md`
- For specific testing APIs, follow that skill's index and read the testing, encrypt, decrypt-acl, public-decrypt, Sepolia, and related references as needed

SDK and clients:

- `zama-sdk/SKILL.md`
- Custom contract calls: `references/custom-contracts.md`
- React/wagmi frontend: `references/react-wagmi-nextjs.md`
- Node, service, and proxy flows: `references/node-and-local.md`
- RPC/relayer/storage configuration: `references/configuration.md`
- Authorization, sessions, and browser security: `references/session-security.md`
- Error handling: `references/errors-events.md` and `references/troubleshooting.md`

Security review:

- `zama-fhevm-security-review/SKILL.md`
- Cross-check against `references/checklist.md` and `references/vulnerability-patterns.md`

## Hardhat Integration Flow

1. Use the core skill first to define the contract's encrypted state, input proofs, ACL, decryption method, and arithmetic boundaries.
2. Use the Hardhat skill to create or repair `packages/contract`, including plugin setup, configuration, TypeChain, deployments, tasks, and test structure.
3. Make the boundary between local/mock behavior and SDK runtime behavior explicit:
   - Hardhat mock tests are appropriate for fast contract tests.
   - Browser/Node SDK flows require a real or compatible relayer runtime.
   - Do not treat mock decrypt as equivalent to production user decrypt.
4. Deployment scripts or deploy tasks should write addresses to `packages/contract/deployments/`, then synchronize them to `packages/frontend/src/contracts/`.
5. Use the SDK skill to select the runtime:
   - Sepolia/browser: `RelayerWeb`
   - Node/service: `RelayerNode`
   - Local cleartext demo: `RelayerCleartext`, provided the local chain and host contracts are compatible
6. Frontend or Node flows must follow the custom-contracts reference: encrypt -> contract write -> read handle -> authorize -> decrypt.
7. If `packages/service` exists, it should only handle backend-private or background responsibilities, such as relayer proxying, public decrypt finalization, on-chain listeners, and smoke tests.

## Artifact Conventions

Hardhat deployments should produce network-specific artifacts:

- `packages/contract/deployments/<network>/...`, preserving the raw Hardhat/Hardhat Deploy output.
- `packages/contract/deployments/addresses.json`, normalized into a frontend-friendly chain ID -> contracts map.
- `packages/frontend/src/contracts/addresses.json`, generated from the canonical artifact.

ABI source priority:

1. TypeChain and Hardhat artifacts.
2. JSON ABIs generated into `packages/frontend/src/contracts`.
3. Lightweight templates may include handwritten ABIs, but the validation checklist must verify that they match the artifacts.

## Deployment Notes

- Sepolia uses Zama's official FHEVM host contracts and relayer configuration. Do not deploy a local/mock host stack to Sepolia.
- Do not put private keys in `.env`. Hardhat vars are also local plaintext; production should use a more secure signer.
- If `.env` stores non-secret RPC URLs, deployment wrappers/tasks must load it explicitly. Do not rely on `pnpm run` to load it automatically.
- When a Hardhat task handles encrypted input or decrypt flows, initialize the plugin CLI API according to the Hardhat skill first.

## Validation Checklist

- `packages/contract`: Hardhat compile, mock tests, and TypeChain generation.
- Contract tests: cover at least encrypted input, computation, ACL, and incorrect proof target cases.
- `packages/frontend`: typecheck, build, and test.
- Local: state clearly whether the setup is mock-only, SDK-compatible local, or points directly to Sepolia.
- Sepolia: the deploy command either succeeds or fails clearly when signer/RPC configuration is missing.
- SDK smoke: when feasible, complete one encrypt/write/read/decrypt flow.
- README: explain the package structure, local/mock/Sepolia differences, frontend configuration, optional service responsibilities, and the secrets/resources users must provide.
