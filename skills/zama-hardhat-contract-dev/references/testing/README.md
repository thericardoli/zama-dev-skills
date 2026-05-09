# Hardhat Testing Overview

This directory explains how to apply the contract patterns from `zama-fhevm-solidity-core` in Hardhat TypeScript tests.

Currently validated against:

- `zama-ai/fhevm-hardhat-template` commit `ec84e1aa1b0a3ef61d9795ef8bf367115b79272f`
- `@fhevm/hardhat-plugin@0.4.2`
- `@fhevm/mock-utils@0.4.2`

## Three Runtime Modes

| Mode | Command | Encryption | Purpose |
| --- | --- | --- | --- |
| in-memory mock | `npx hardhat test` | mock | Fast unit tests and CI |
| localhost mock | `npx hardhat node` + `--network localhost` | mock | Local frontend/task integration |
| Sepolia | `--network sepolia` | real | Real end-to-end validation |

Mock suite:

```ts
beforeEach(async function () {
  if (!fhevm.isMock) {
    this.skip();
  }
});
```

Sepolia suite:

```ts
before(async function () {
  if (fhevm.isMock) {
    this.skip();
  }
});
```

## Minimal Test Skeleton

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

## File Guide

- `encrypt.md`: how to test encrypted input, target/user binding, and multi-value input.
- `decrypt-acl.md`: how to test user decrypt, ACLs, and unauthorized failures.
- `public-decrypt.md`: how to test public decrypt and public reveal flows.
- `sepolia.md`: how to write real-network e2e tests.
- `erc7984.md`: how to test ERC7984 confidential tokens.
