# Foundry Orchestration Path

When `packages/contract` uses Foundry/Forge plus `forge-fhevm`, use this file to compose the relevant skills.

## Recommended Structure

```text
packages/
├── contract/
│   ├── src/
│   ├── test/
│   ├── script/
│   ├── scripts/
│   ├── deployments/
│   ├── foundry.toml
│   └── package.json
├── frontend/
│   └── src/
└── service/
```

## Skills and References to Read

Contract logic:

- `zama-fhevm-solidity-core/SKILL.md`
- For APIs, read `zama-fhevm-solidity-core/references/api.md`
- For protocol and architecture context, read `zama-fhevm-solidity-core/references/overview.md`

Foundry project and tests:

- `zama-foundry-forge-fhevm/SKILL.md`
- To create or fix configuration: `references/foundry-project.md`
- To deploy locally or to Sepolia: `references/deploy.md`
- For specific testing APIs, follow that skill's index and read the testing, encrypt, decrypt, ACL, fuzz, and related references as needed

SDK and clients:

- `zama-sdk/SKILL.md`
- Custom contract calls: `references/custom-contracts.md`
- React/wagmi frontend: `references/react-wagmi-nextjs.md`
- Node, local cleartext, and service flows: `references/node-and-local.md`
- RPC/relayer/storage configuration: `references/configuration.md`
- Authorization, sessions, and browser security: `references/session-security.md`
- Error handling: `references/errors-events.md` and `references/troubleshooting.md`

Security review:

- `zama-fhevm-security-review/SKILL.md`
- Cross-check against `references/checklist.md` and `references/vulnerability-patterns.md`

## Foundry Integration Flow

1. Use the core skill first to define the contract's encrypted state, input proofs, ACL, decryption method, and arithmetic boundaries.
2. Use the Foundry skill to create or repair `packages/contract`, including `foundry.toml`, Soldeer dependencies, remappings, Forge tests, and deployment scripts.
3. Use the Foundry deployment reference to handle both local layers:
   - The `forge-fhevm` local cleartext host stack on Anvil.
   - The dApp contract deployment.
4. Deployment scripts should write addresses to `packages/contract/deployments/`, then synchronize them to `packages/frontend/src/contracts/`.
5. Use the SDK skill to select the runtime:
   - Local cleartext: `RelayerCleartext`
   - Sepolia/browser: `RelayerWeb`
   - Node/service: `RelayerNode`
6. Frontend or Node flows must follow the custom-contracts reference: encrypt -> contract write -> read handle -> authorize -> decrypt.
7. If `packages/service` exists, it should only handle backend-private or background responsibilities, such as relayer proxying, public decrypt finalization, on-chain listeners, and smoke tests.

## Artifact Conventions

Foundry deployment scripts should write network-specific artifacts:

- `packages/contract/deployments/local.json`
- `packages/contract/deployments/sepolia.json`
- `packages/contract/deployments/addresses.json`
- `packages/frontend/src/contracts/addresses.json`

`addresses.json` should be grouped by chain ID. Do not use a single `deployment.json` that overwrites every network.

ABI source priority:

1. Generate or copy ABI data from Foundry compilation artifacts.
2. Lightweight templates may include handwritten ABIs, but the validation checklist must verify that they match the compiled artifacts.

## Deployment Notes

- Sepolia does not require running `forge-fhevm/deploy-local.sh`.
- For testnet or production deployment, use a Foundry keystore, hardware wallet, or controlled signer. Do not put private keys in `.env`.
- Root scripts may call deployment wrappers inside `packages/contract`; the wrapper is responsible for loading `.env`, checking `SEPOLIA_RPC_URL`, `DEPLOYER_ACCOUNT`, keystore configuration, and optional verification keys.
- If deployment scripts write files, Foundry `fs_permissions` must cover `packages/contract/deployments` and `packages/frontend/src/contracts`.

## Validation Checklist

- `packages/contract`: Soldeer install, Forge build, and Forge tests.
- Contract tests: cover at least encrypted input, computation, ACL, and incorrect proof target cases.
- `packages/frontend`: typecheck, build, and test.
- Local: document clear steps for Anvil plus the FHEVM host stack plus dApp deployment.
- Sepolia: the deploy command either succeeds or fails clearly when env/keystore configuration is missing.
- SDK smoke: when feasible, complete one encrypt/write/read/decrypt flow.
- README: explain the package structure, local/Sepolia flows, frontend configuration, optional service responsibilities, and the secrets/resources users must provide.
