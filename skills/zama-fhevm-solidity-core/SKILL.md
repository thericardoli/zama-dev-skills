---
name: zama-fhevm-solidity-core
description: Use this skill when writing, modifying, or explaining confidential smart contracts with Zama FHEVM Solidity. Applies to @fhevm/solidity, FHE, euint/externalEuint, ACL, encrypted inputs, decryption flows, ZamaConfig, and ERC7984 integration.
---

# Zama FHEVM Solidity Core

## Introduction

This skill is the main entry point for Zama FHEVM Solidity development. It helps agents understand and implement confidential smart contracts based on `@fhevm/solidity`.

The core FHEVM Solidity workflow is to declare encrypted types in Solidity, verify encrypted inputs submitted off-chain, compute in the encrypted domain, use ACL rules to control later handle usage and decryption permissions, and support user decrypt or public decrypt when appropriate.

## Usage Principles

- Read the current project's dependencies and configuration before choosing API syntax.
- If you are unsure about Zama Protocol, official repositories, or the overall architecture, read the overview first.
- If you are unsure about types or function signatures, read the API reference and treat the source installed in the current project as authoritative.
- For specific development tasks, read only the relevant pattern file instead of loading all references at once.

## References

- [references/overview.md](references/overview.md): Introduces Zama Protocol, the problems solved by fhevm-solidity, the overall architecture, and official repository entry points.
- [references/api.md](references/api.md): Lists common encrypted types, `FHE` APIs, ACL APIs, decryption APIs, configuration types, and debugging entry points.
- [references/patterns/encryption.md](references/patterns/encryption.md): External encrypted inputs, `FHE.fromExternal`, and Hardhat/Foundry encrypted input testing patterns.
- [references/patterns/decryption.md](references/patterns/decryption.md): User decrypt, public decrypt, on-chain signature verification, and common decryption mistakes.
- [references/patterns/acl.md](references/patterns/acl.md): `allowThis`, `allow`, `allowTransient`, public decrypt permissions, and multi-user permission propagation.
- [references/patterns/operations.md](references/patterns/operations.md): Arithmetic, comparisons, bit operations, type selection, scalar operations, and overflow-safe updates.
- [references/patterns/branching.md](references/patterns/branching.md): `FHE.select`, encrypted conditions, fixed-count loops, asynchronous public branching, and error handling.
- [references/patterns/randomness.md](references/patterns/randomness.md): `FHE.randE*`, bounded randomness, transaction constraints, ACL, and game/lottery patterns.
- [references/patterns/reorgs.md](references/patterns/reorgs.md): Two-phase ACL authorization for high-value secrets and reorg risk handling.
- [references/patterns/erc7984.md](references/patterns/erc7984.md): Minimal integration, transfers, balance reads, and extension considerations for OpenZeppelin ERC7984 confidential tokens.

## Minimal Safety Reminder

Do not treat a plain `bytes32` as a verified encrypted input. Do not forget to set ACL permissions on new handles. Do not mark sensitive state as publicly decryptable just to make debugging easier.
