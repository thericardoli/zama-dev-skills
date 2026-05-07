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

## 记住这几个坑

- `createEncryptedInput(contractAddress, userAddress)` 同时绑定 target contract 和 user。
- `encrypt()` 返回 `handles` 和 `inputProof`，不是 `proof`。
- Solidity 的 `externalEuintXX` 在 ABI/TypeChain 中通常是 `bytes32`。
- `userDecryptEuint` 会检查 ACL；`fhevm.debugger.decryptEuint` 是 mock/debug 工具，不应用来证明权限。
- Hardhat task 里要先 `await fhevm.initializeCLIApi()`。
- mock 测试和 Sepolia e2e 测试不要混在一个无条件 suite 里。
