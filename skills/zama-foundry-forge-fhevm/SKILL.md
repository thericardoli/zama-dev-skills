---
name: zama-foundry-forge-fhevm
description: Use this skill when developing, testing, or deploying Zama FHEVM confidential contracts with Foundry and forge-fhevm. Covers FhevmTest, forge test, Foundry project setup, Solidity 0.8.27, Cancun EVM, encrypted input, direct/public/user decrypt, ACL, ERC7984 confidential tokens, fuzzing, and local/Sepolia/mainnet deployment.
---

# Zama Foundry forge-fhevm

`forge-fhevm` is Zama's Foundry-native toolkit for FHEVM testing and local development. When Forge tests inherit `FhevmTest`, it deploys real fhEVM host contracts in the test environment, including `FHEVMExecutor`, `ACL`, `InputVerifier`, and `KMSVerifier`, and tracks encrypted handles in a local plaintext database so tests can encrypt, compute, decrypt, and assert entirely within Foundry.

Contracts are still written with `@fhevm/solidity`: encrypted types, `FHE.fromExternal`, `FHE.add/select/...`, `FHE.allowThis`, `FHE.allow`, `FHE.makePubliclyDecryptable`, and the usual FHEVM patterns.

## Which Reference to Read First

- Creating or fixing a Foundry project: read `references/foundry-project.md`
- Writing deployment scripts: read `references/deploy.md`
- Looking up the forge-fhevm API: read `references/api/README.md`
- Getting oriented before writing tests: read `references/testing/README.md`
- Testing encrypted inputs: read `references/testing/encrypt.md`
- Testing decryption: read `references/testing/decrypt.md`
- Testing ACL and permissions: read `references/testing/acl.md`
- Testing ERC7984 tokens: read `references/testing/erc7984.md`
- Fuzzing, failure paths, and troubleshooting: read `references/testing/fuzz-and-errors.md`

## Usage Principles

- Inspect the project's installed `forge-fhevm/FhevmTest.sol`, `deploy-local.sh`, and `deploy.sh` before applying examples from these references.
- `forge-fhevm` currently requires Solidity `^0.8.27` and `evm_version = "cancun"`.
- Do not pin Soldeer dependencies such as `@fhevm-solidity` or `@encrypted-types` to `latest`; start from the verified versions in this skill, and when upgrading, query the registry and update `foundry.toml`, `soldeer.lock`, and `remappings.txt` together.
- Call `super.setUp()` first when overriding `setUp()` in Forge tests.
- `FhevmTest.decrypt` is a test-only plaintext read and does not enforce ACL checks; permission-sensitive tests must cover `publicDecrypt` or `userDecrypt`.
- Do not store private keys in `.env` files or scripts for real deployments; use the Foundry keystore, call `vm.startBroadcast()` in scripts, and select the signer on the command line with `forge script --account <name>`.
- An Anvil-only local demo deploy wrapper should set `LOCAL_STATE_RPC_NAMESPACE=anvil` explicitly to avoid empty `cast client` detection; if deployment scripts write JSON, configure `fs_permissions` in `foundry.toml`.
- The local cleartext FHEVM stack is only for development and testing; it is not a production privacy deployment.

## Upstream Source of Truth

The API and deployment guidance in this skill follows the `zama-ai/forge-fhevm` source and docs, especially `src/FhevmTest.sol`, `docs/api/*.md`, `docs/guides/*.md`, `deploy-local.sh`, and `deploy.sh`. If upstream API docs disagree with the installed source in the current project, treat the installed source as authoritative.
