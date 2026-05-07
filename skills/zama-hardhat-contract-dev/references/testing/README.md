# Hardhat 测试总览

本目录说明如何把 `zama-fhevm-solidity-core` 的合约模式落到 Hardhat TypeScript 测试。

当前核对过的来源：

- `zama-ai/fhevm-hardhat-template` commit `ec84e1aa1b0a3ef61d9795ef8bf367115b79272f`
- `@fhevm/hardhat-plugin@0.4.2`
- `@fhevm/mock-utils@0.4.2`

## 三种运行模式

| 模式 | 命令 | 加密 | 用途 |
| --- | --- | --- | --- |
| in-memory mock | `npx hardhat test` | mock | 快速单元测试、CI |
| localhost mock | `npx hardhat node` + `--network localhost` | mock | 前端/task 本地联调 |
| Sepolia | `--network sepolia` | real | 真实端到端验证 |

mock suite：

```ts
beforeEach(async function () {
  if (!fhevm.isMock) {
    this.skip();
  }
});
```

Sepolia suite：

```ts
before(async function () {
  if (fhevm.isMock) {
    this.skip();
  }
});
```

## 最小测试骨架

```ts
import { FhevmType } from "@fhevm/hardhat-plugin";
import { HardhatEthersSigner } from "@nomicfoundation/hardhat-ethers/signers";
import { expect } from "chai";
import { ethers, fhevm } from "hardhat";
import { ConfidentialVault, ConfidentialVault__factory } from "../types";

describe("ConfidentialVault", function () {
  let alice: HardhatEthersSigner;
  let bob: HardhatEthersSigner;
  let vault: ConfidentialVault;
  let vaultAddress: string;

  before(async function () {
    [alice, bob] = await ethers.getSigners();
  });

  beforeEach(async function () {
    if (!fhevm.isMock) this.skip();

    const factory = (await ethers.getContractFactory("ConfidentialVault")) as ConfidentialVault__factory;
    vault = (await factory.deploy()) as ConfidentialVault;
    vaultAddress = await vault.getAddress();
  });

  it("deposits encrypted amount", async function () {
    const encrypted = await fhevm
      .createEncryptedInput(vaultAddress, alice.address)
      .add64(100n)
      .encrypt();

    await vault.connect(alice).deposit(encrypted.handles[0], encrypted.inputProof);

    const handle = await vault.balanceOf(alice.address);
    const clear = await fhevm.userDecryptEuint(FhevmType.euint64, handle, vaultAddress, alice);
    expect(clear).to.eq(100n);
  });
});
```

## 文件导览

- `encrypt.md`：如何测试 encrypted input、target/user 绑定和多值输入。
- `decrypt-acl.md`：如何测试 user decrypt、ACL、未授权失败。
- `public-decrypt.md`：如何测试 public decrypt 和公开 reveal。
- `sepolia.md`：如何写真实网络 e2e。
- `erc7984.md`：如何测试 ERC7984 confidential token。

## 断言原则

- FHE 运算结果用 `userDecrypt*` 或 `publicDecrypt*` 验证。
- ACL 测试不能只检查 handle 非零。
- mock debug decrypt 只能辅助排查，不能替代权限测试。
- Sepolia 测试要少而准，覆盖真实 encrypted input、交易确认、decrypt。
