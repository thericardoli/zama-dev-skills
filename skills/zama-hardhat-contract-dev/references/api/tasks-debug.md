# Hardhat Task 和 Debug API

自定义 task 与测试不同：必须显式初始化 CLI API。

```ts
import { FhevmType } from "@fhevm/hardhat-plugin";
import { task } from "hardhat/config";
import type { TaskArguments } from "hardhat/types";

task("task:decrypt-balance")
  .addParam("address", "Vault address")
  .setAction(async function (args: TaskArguments, hre) {
    const { ethers, fhevm } = hre;
    await fhevm.initializeCLIApi();

    const [user] = await ethers.getSigners();
    const vault = await ethers.getContractAt("ConfidentialVault", args.address);
    const handle = await vault.balanceOf(user.address);

    const clear = await fhevm.userDecryptEuint(FhevmType.euint64, handle, args.address, user);
    console.log(clear);
  });
```

## 写交易 task

```ts
task("task:deposit")
  .addParam("address", "Vault address")
  .addParam("amount", "Amount")
  .setAction(async function (args, hre) {
    const { ethers, fhevm } = hre;
    await fhevm.initializeCLIApi();

    const [user] = await ethers.getSigners();
    const amount = BigInt(args.amount);
    const vault = await ethers.getContractAt("ConfidentialVault", args.address);

    const encrypted = await fhevm
      .createEncryptedInput(args.address, user.address)
      .add64(amount)
      .encrypt();

    const tx = await vault.connect(user).deposit(encrypted.handles[0], encrypted.inputProof);
    await tx.wait();
  });
```

## 内置 fhevm 命令

插件提供：

```bash
npx hardhat --network sepolia fhevm user-decrypt --type euint64 --handle 0x... --user 0 --contract 0x...
npx hardhat --network sepolia fhevm public-decrypt --type euint64 --handle 0x...
npx hardhat --network sepolia fhevm check-fhevm-compatibility --address 0x...
npx hardhat fhevm resolve-fhevm-config --acl 0x... --kms 0x...
```

## 排查 revert

```ts
try {
  const tx = await vault.connect(user).deposit(encrypted.handles[0], encrypted.inputProof);
  await tx.wait();
} catch (e) {
  await hre.fhevm.tryParseFhevmError(e, { encryptedInput: encrypted, out: "console" });
  throw e;
}
```

适合定位 encrypted input 的 contract/user 绑定错误、FHEVM host config 错误、handle 类型错误等。
