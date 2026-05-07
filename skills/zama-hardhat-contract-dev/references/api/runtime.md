# Runtime API

`@fhevm/hardhat-plugin` 扩展 Hardhat Runtime Environment：

```ts
import { fhevm } from "hardhat";
// 或
import * as hre from "hardhat";
await hre.fhevm.getRelayerMetadata();
```

`hardhat.config.ts` 必须有：

```ts
import "@fhevm/hardhat-plugin";
```

## 运行模式

```ts
if (!fhevm.isMock) {
  this.skip();
}
```

`fhevm.isMock`：

- `true`：Hardhat in-memory 或 Hardhat node mock 环境，适合单元测试和本地联调。
- `false`：Sepolia/mainnet 等真实 FHEVM 环境，使用真实加密和 relayer。

## CLI task 初始化

自定义 Hardhat task 必须先初始化：

```ts
task("task:decrypt-balance").setAction(async (_args, hre) => {
  const { fhevm } = hre;
  await fhevm.initializeCLIApi();
});
```

普通 `npx hardhat test` 由插件接管初始化，不需要手动调用。

## 配置检查

部署或连到远程网络后，检查合约是否使用正确 FHEVM host config：

```ts
await fhevm.assertCoprocessorInitialized(contract, "ConfidentialVault");
const cfg = await fhevm.getCoprocessorConfig(await contract.getAddress());
```

命令行也可用：

```bash
npx hardhat --network sepolia fhevm check-fhevm-compatibility --address 0x...
```

## 事件和 HCU

```ts
const receipt = await tx.wait();
const events = fhevm.parseCoprocessorEvents(receipt?.logs);
const hcu = fhevm.computeTransactionHCU(receipt!);
```

用来排查 FHE executor 事件和估算 FHE 操作成本。普通业务断言不要只依赖 HCU。

## 错误排查

```ts
try {
  await tx.wait();
} catch (e) {
  await fhevm.tryParseFhevmError(e, { encryptedInput, out: "console" });
  throw e;
}
```

常见能解析的问题包括 encrypted input 的 target/user 绑定错误、handle 类型不匹配、ACL 缺失等。
