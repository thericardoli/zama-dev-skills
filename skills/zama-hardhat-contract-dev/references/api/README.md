# Hardhat FHEVM API Overview

Start with the type definitions installed in the project at `node_modules/@fhevm/hardhat-plugin`. This document is organized around `@fhevm/hardhat-plugin@0.4.2` and the official template patterns.

| Scenario | Read | Key APIs |
| --- | --- | --- |
| HRE and runtime mode | `runtime.md` | `fhevm.isMock`, `initializeCLIApi`, `assertCoprocessorInitialized` |
| encrypted input | `encrypted-input.md` | `createEncryptedInput(...).addXX(...).encrypt()` |
| user/public decrypt | `decrypt.md` | `userDecryptEuint`, `publicDecryptEuint`, generic decrypt |
| Hardhat tasks / debug | `tasks-debug.md` | `initializeCLIApi`, `tryParseFhevmError`, `fhevm.debugger` |

## The Three Most Common Steps

```ts
import { FhevmType } from "@fhevm/hardhat-plugin";
import { ethers, fhevm } from "hardhat";

const encrypted = await fhevm
  .createEncryptedInput(contractAddress, alice.address)
  .add64(100n)
  .encrypt();

await vault.connect(alice).deposit(encrypted.handles[0], encrypted.inputProof);

const handle = await vault.balanceOf(alice.address);
const clear = await fhevm.userDecryptEuint(FhevmType.euint64, handle, contractAddress, alice);
```
