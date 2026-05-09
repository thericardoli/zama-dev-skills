---
name: zama-hardhat-contract-dev
description: Use this skill when developing, testing, and deploying Zama FHEVM confidential contracts with Hardhat. It covers fhevm-hardhat-template, @fhevm/hardhat-plugin, the Hardhat mock environment, TypeScript tests, encrypted input, user/public decrypt, ACLs, ERC7984 confidential tokens, Hardhat tasks, localhost/Sepolia/mainnet deployments, and contract verification.
---

# Zama Hardhat Contract Dev

`@fhevm/hardhat-plugin` is Zama's Hardhat-native FHEVM development plugin. It extends the Hardhat Runtime Environment with `hre.fhevm` / `import { fhevm } from "hardhat"` so you can generate encrypted input, run user/public decrypt, initialize CLI task environments, and deploy FHEVM host contracts on Hardhat mock networks.

Contracts are still written using the `@fhevm/solidity` patterns: encrypted types, `FHE.fromExternal`, `FHE.add/select/...`, `FHE.allowThis`, `FHE.allow`, `FHE.makePubliclyDecryptable`, and related APIs.

## Which Reference to Read First

- Creating or repairing a Hardhat project: read `references/hardhat-project.md`
- Looking up the Hardhat FHEVM API: read `references/api/README.md`
- Writing deployment scripts: read `references/deploy.md`
- Getting oriented before writing tests: read `references/testing/README.md`
- Testing encrypted input: read `references/testing/encrypt.md`
- Testing decrypt / ACL behavior: read `references/testing/decrypt-acl.md`
- Testing public decrypt: read `references/testing/public-decrypt.md`
- Writing Sepolia end-to-end tests: read `references/testing/sepolia.md`
- Testing ERC7984 tokens: read `references/testing/erc7984.md`

## Operating Principles

- Inspect the project's actual `package.json`, `hardhat.config.ts`, `types/`, and lockfile before applying examples from these references.
- The current template uses Node `>=20`, Solidity `0.8.27`, and `evmVersion = "cancun"`; defer to the current project's configuration when it differs.
- `hardhat.config.ts` must import `@fhevm/hardhat-plugin`; otherwise the `fhevm` HRE API will not exist.
- In TypeScript tests, prefer importing `ethers, fhevm` from `hardhat` and `FhevmType` from `@fhevm/hardhat-plugin`.
- Mock tests where `fhevm.isMock` is true may use local decrypt helpers. Sepolia/mainnet are real FHEVM environments and should be tested in separate suites.
- Hardhat tasks must call `await fhevm.initializeCLIApi()` before using the CLI API. Regular `hardhat test` runs do not require a manual call.
- Do not put private keys in `.env` for deployments. Live networks (Sepolia/mainnet) must not fall back to the default Hardhat test mnemonic, placeholder RPC URLs, or empty signers. Missing signer/RPC configuration must fail fast with clear instructions for the required Hardhat vars or secret-manager setup.
- Local `hardhat` / `localhost` networks may use the public test mnemonic. Sepolia/mainnet must use an independent, network-specific signer such as `SEPOLIA_MNEMONIC`, a hardware wallet, a multisig, or a managed secret manager. Hardhat vars are stored locally in plaintext and are not appropriate for high-value production keys.

## Upstream Sources

The API and deployment guidance in this skill are based on the versions of `@fhevm/hardhat-plugin`, `@fhevm/mock-utils`, `@fhevm/solidity`, and `zama-ai/fhevm-hardhat-template` installed in the target project. If these references disagree with the project's dependencies, trust the project source and TypeScript type definitions.
