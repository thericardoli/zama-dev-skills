# Hardhat FHEVM API 总览

先看项目安装的 `node_modules/@fhevm/hardhat-plugin` 类型定义。本文按 `@fhevm/hardhat-plugin@0.4.2` 和官方 template 写法整理。

| 场景 | 读哪个文件 | 关键 API |
| --- | --- | --- |
| HRE 和运行模式 | `runtime.md` | `fhevm.isMock`、`initializeCLIApi`、`assertCoprocessorInitialized` |
| encrypted input | `encrypted-input.md` | `createEncryptedInput(...).addXX(...).encrypt()` |
| user/public decrypt | `decrypt.md` | `userDecryptEuint`、`publicDecryptEuint`、generic decrypt |
| Hardhat task / debug | `tasks-debug.md` | `initializeCLIApi`、`tryParseFhevmError`、`fhevm.debugger` |

## 最常用三步

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
