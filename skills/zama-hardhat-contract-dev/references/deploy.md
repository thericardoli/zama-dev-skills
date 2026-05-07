# Hardhat 部署

本文件只讨论 FHEVM dApp 合约部署。Hardhat plugin 会在 mock 网络里准备 FHEVM host contracts；Sepolia 使用 Zama 官方 FHEVM 网络配置。

## 密钥和变量

不要把 private key 写进 `.env`、脚本或 CI log。模板使用 Hardhat vars：

```bash
npx hardhat vars set MNEMONIC
npx hardhat vars set INFURA_API_KEY
npx hardhat vars set ETHERSCAN_API_KEY
npx hardhat vars setup
```

注意：Hardhat vars 存在项目代码之外，适合避免把 secret 提交进仓库，但它不是加密 keystore。生产部署优先用硬件钱包、multisig、KMS 或受控 secret manager。

`hardhat.config.ts` 用 `vars.get`：

```ts
import { vars } from "hardhat/config";

const MNEMONIC = vars.get("MNEMONIC", "test test test test test test test test test test test junk");
const INFURA_API_KEY = vars.get("INFURA_API_KEY", "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz");
```

不要写：

```ts
const PRIVATE_KEY = process.env.PRIVATE_KEY;
```

## deploy 脚本

`deploy/001_deploy_vault.ts`：

```ts
import type { DeployFunction } from "hardhat-deploy/types";
import type { HardhatRuntimeEnvironment } from "hardhat/types";

const func: DeployFunction = async function (hre: HardhatRuntimeEnvironment) {
  const { deployer } = await hre.getNamedAccounts();
  const { deploy } = hre.deployments;

  const deployed = await deploy("ConfidentialVault", {
    from: deployer,
    args: [],
    log: true,
  });

  console.log("ConfidentialVault", deployed.address);
};

export default func;
func.id = "deploy_confidential_vault";
func.tags = ["ConfidentialVault"];
```

如果构造函数需要 owner、token、threshold 等参数，显式从 Hardhat vars、deploy 参数或 network config 读取，不要默认复用 deployer。

## Localhost mock

终端 1：

```bash
npm run chain
```

终端 2：

```bash
npm run deploy:localhost
# 或
npx hardhat deploy --network localhost
```

本地交互：

```bash
npx hardhat --network localhost task:deposit --address 0x... --amount 100
npx hardhat --network localhost task:decrypt-balance --address 0x...
```

注意：

- `npx hardhat test` 会在 in-memory mock 网络内初始化 FHEVM host，不需要先启动 node。
- `npx hardhat node` 会提供持久 mock 状态，适合前端或 task 联调。
- mock 模式不提供生产隐私保证。

## Sepolia

Sepolia 使用真实 FHEVM 加密和 Zama relayer，不跑 mock-only 断言。

前置：

```bash
npx hardhat vars set MNEMONIC
npx hardhat vars set INFURA_API_KEY
npx hardhat vars set ETHERSCAN_API_KEY
```

部署：

```bash
npx hardhat deploy --network sepolia
npx hardhat verify --network sepolia <CONTRACT_ADDRESS>
```

部署后检查：

```bash
npx hardhat --network sepolia fhevm check-fhevm-compatibility --address <CONTRACT_ADDRESS>
npx hardhat test --network sepolia
```

Sepolia 注意事项：

- 确认合约继承 `ZamaEthereumConfig`。
- 确认前端/task 生成 encrypted input 时使用的 contract address、user address、chain id、relayer config 与 Sepolia 一致。
- Sepolia e2e 慢，给测试设置更长 timeout。
- 不要把 mock-only `fhevm.debugger.decrypt*` 或 `fhevm.isMock` suite 直接跑到 Sepolia。

## Mainnet

Mainnet 部署流程和 Sepolia 类似，但必须先确认当前 `@fhevm/solidity`、`@fhevm/hardhat-plugin`、Zama SDK、Zama docs 已支持目标 mainnet。插件 README 提到 mainnet encrypted input / decrypt 需要配置 Zama API key：

```bash
npx hardhat vars set ZAMA_FHEVM_API_KEY
npx hardhat vars get ZAMA_FHEVM_API_KEY
```

Mainnet 注意事项：

- 使用硬件钱包、multisig 或受控 signer；不要把生产 mnemonic/private key 放在 `.env`。
- 在 fork 或 Sepolia 上演练 deploy、verify、constructor args、owner/pause 初始化。
- 对所有 `FHE.makePubliclyDecryptable` 做产品级审查。
- 部署后执行最小真实流程：encrypted input 交易、user decrypt、必要时 public decrypt。
- 若当前依赖没有 mainnet host config，不要硬编码 Sepolia/local 地址冒充 mainnet。
