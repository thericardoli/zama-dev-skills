# Sepolia e2e 测试

Sepolia 使用真实 FHEVM 加密，测试慢且需要测试 ETH。只保留少量端到端路径，不把 mock 单元测试整套搬过去。

## 基本结构

```ts
import { FhevmType } from "@fhevm/hardhat-plugin";
import { expect } from "chai";
import { deployments, ethers, fhevm } from "hardhat";

describe("ConfidentialVaultSepolia", function () {
  before(async function () {
    if (fhevm.isMock) {
      this.skip();
    }
  });

  it("deposits and decrypts", async function () {
    this.timeout(4 * 40_000);

    const [alice] = await ethers.getSigners();
    const deployment = await deployments.get("ConfidentialVault");
    const vault = await ethers.getContractAt("ConfidentialVault", deployment.address);

    const encrypted = await fhevm
      .createEncryptedInput(deployment.address, alice.address)
      .add64(100n)
      .encrypt();

    const tx = await vault.connect(alice).deposit(encrypted.handles[0], encrypted.inputProof);
    await tx.wait();

    const handle = await vault.balanceOf(alice.address);
    const clear = await fhevm.userDecryptEuint(FhevmType.euint64, handle, deployment.address, alice);
    expect(clear).to.be.greaterThanOrEqual(100n);
  });
});
```

## 注意事项

- 先部署：`npx hardhat deploy --network sepolia`。
- 如果 `deployments.get(...)` 找不到，提示用户先部署。
- 不要依赖初始状态为 0；Sepolia 合约可能已有历史状态。
- 给测试设置 timeout。
- 尽量只跑一个最小真实路径：encrypt input、write tx、read handle、user decrypt。
- 不要在 Sepolia suite 使用 `fhevm.debugger.decrypt*`。

## 配置检查

```bash
npx hardhat --network sepolia fhevm check-fhevm-compatibility --address 0x...
```

如果检查失败，先看合约是否继承 `ZamaEthereumConfig`，再看 `@fhevm/solidity` 版本和网络配置。
