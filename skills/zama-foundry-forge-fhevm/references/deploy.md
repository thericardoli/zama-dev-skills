# Foundry 部署

本文件只讨论“FHEVM dApp 合约如何部署”。`forge-fhevm` 自带的 `deploy-local.sh` / `deploy.sh` 部署的是 cleartext FHEVM host stack，用于本地或私有开发链；不要把它当成 Sepolia/mainnet dApp 部署步骤。

实际部署时不要把 private key 写进 `.env`、脚本、命令历史或 CI log。dApp 部署应使用 Foundry keystore：用 `cast wallet import` 保存加密 keystore，用 `forge script --account <name>` 选择 signer。

合约应继承 `ZamaEthereumConfig`，由 `@fhevm/solidity` 根据网络配置 FHEVM host contracts：

```solidity
import {FHE, euint64, externalEuint64} from "@fhevm/solidity/lib/FHE.sol";
import {ZamaEthereumConfig} from "@fhevm/solidity/config/ZamaConfig.sol";

contract ConfidentialVault is ZamaEthereumConfig {
    mapping(address => euint64) private _balances;

    function deposit(externalEuint64 encryptedAmount, bytes calldata proof) external {
        euint64 amount = FHE.fromExternal(encryptedAmount, proof);
        euint64 next = FHE.add(_balances[msg.sender], amount);
        _balances[msg.sender] = next;
        FHE.allowThis(next);
        FHE.allow(next, msg.sender);
    }
}
```

## Signer / keystore

创建或导入部署账户：

```bash
cast wallet import zama-sepolia-deployer --interactive
cast wallet list
cast wallet address --account zama-sepolia-deployer
```

`cast wallet import` 默认把加密 keystore 保存到 `~/.foundry/keystores`。需要要求用户交互式输入 private key 和 keystore password，避免把 private key 写入 shell 历史或 `.env`。

`.env` 只放非私钥配置：

```bash
SEPOLIA_RPC_URL=https://...
MAINNET_RPC_URL=https://...
ETHERSCAN_API_KEY=...
DEPLOYER_ACCOUNT=zama-sepolia-deployer
OWNER=0x...
```

部署脚本不要读取 private key。让 `forge script` 的 wallet 选项负责签名：

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import {Script, console2} from "forge-std/Script.sol";
import {ConfidentialVault} from "../src/ConfidentialVault.sol";

contract DeployConfidentialVault is Script {
    function run() external returns (ConfidentialVault vault) {
        address owner = vm.envAddress("OWNER");

        vm.startBroadcast();
        vault = new ConfidentialVault(owner);
        vm.stopBroadcast();

        console2.log("ConfidentialVault", address(vault));
    }
}
```

要点：

- 不要写 `uint256 deployerPk = vm.envUint("PRIVATE_KEY")`。
- 不要用 `vm.startBroadcast(deployerPk)` 读取 env 私钥。
- 构造函数里的 owner、admin、token、threshold 等参数从 env 读取地址或显式传参，不要默认等于 deployer。
- 如果需要更高安全级别，mainnet 优先使用硬件钱包、multisig、KMS 或受控签名流程；keystore 适合开发和中低风险部署账户。

## Local

Local 有两层部署：

1. 把 cleartext FHEVM host contracts 放到本地链的标准地址。
2. 部署你的 dApp 合约。

启动 Anvil：

```bash
anvil
```

在另一个终端运行 `forge-fhevm` 的本地 host stack 脚本。Soldeer 项目通常在 `dependencies/forge-fhevm-<version>/deploy-local.sh`，submodule 项目通常在 `lib/forge-fhevm/deploy-local.sh`：

```bash
./dependencies/forge-fhevm-<version>/deploy-local.sh
```

非默认端口：

```bash
./dependencies/forge-fhevm-<version>/deploy-local.sh --anvil-port 8546
```

多个本地节点：

```bash
./dependencies/forge-fhevm-<version>/deploy-local.sh --anvil-port 8545 --anvil-port 8546
```

复用已 build artifacts：

```bash
./dependencies/forge-fhevm-<version>/deploy-local.sh --skip-build --anvil-port 8545
```

部署 dApp 时仍优先走 keystore。第一次本地调试可以把 Anvil 的公开测试私钥交互式导入一个本地账户：

```bash
cast wallet import local-anvil --interactive

OWNER=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \
forge script script/DeployConfidentialVault.s.sol:DeployConfidentialVault \
  --rpc-url http://127.0.0.1:8545 \
  --account local-anvil \
  --broadcast
```

Local 注意事项：

- `deploy-local.sh` 不需要 `.env`，默认使用 Anvil key、mock gateway、mock KMS/input signer。
- 它通过本地 RPC 的 `setCode` / `setStorageAt` 把 host contracts materialize 到 `FHEVMHostAddresses.sol` 的固定地址；只适合 Anvil/Hardhat 这类本地节点。
- 合约测试继承 `FhevmTest` 时不需要先跑 `deploy-local.sh`；`super.setUp()` 会在 Forge 测试环境内部署 host contracts。
- 本地 cleartext stack 中 encrypted values 实际以明文跟踪，不能用来证明生产隐私安全。

## Sepolia

Sepolia 部署 dApp 时不需要先部署 `forge-fhevm` 的 host stack；使用 Zama 官方 Sepolia FHEVM host contracts 和 relayer 配置。当前官方文档列出的 Sepolia host 地址包括 `FHEVM_EXECUTOR_CONTRACT`、`ACL_CONTRACT`、`HCU_LIMIT_CONTRACT`、`KMS_VERIFIER_CONTRACT`、`INPUT_VERIFIER_CONTRACT`，relayer 为 `https://relayer.testnet.zama.org`，gateway chain id 为 `10901`。

`.env.sepolia` 示例，不包含 private key：

```bash
SEPOLIA_RPC_URL=https://...
ETHERSCAN_API_KEY=...
DEPLOYER_ACCOUNT=zama-sepolia-deployer
OWNER=0x...
```

部署：

```bash
source .env.sepolia

forge script script/DeployConfidentialVault.s.sol:DeployConfidentialVault \
  --rpc-url "$SEPOLIA_RPC_URL" \
  --account "$DEPLOYER_ACCOUNT" \
  --broadcast \
  --verify \
  --etherscan-api-key "$ETHERSCAN_API_KEY"
```

Sepolia 注意事项：

- 确认合约继承 `ZamaEthereumConfig`，并且当前 `@fhevm/solidity` 版本支持 Sepolia。
- 前端/脚本加密输入时，user、contract、chain id、relayer config 必须与 Sepolia 一致。
- Sepolia 是测试网；不要放真实敏感数据或资金假设。
- 不要在 Sepolia 上运行 `forge-fhevm/deploy-local.sh`。`deploy.sh` 只适合你自己部署 cleartext FHEVM stack 的远程开发链，不是接入 Zama Sepolia 的常规步骤。
- 部署后至少跑一条真实 encrypted input 交易和一次 user decrypt/public decrypt 验证，而不只是 `forge verify-contract`。

## Mainnet

Mainnet dApp 部署脚本与 Sepolia 形式相同，但发布前必须先确认当前官方 `@fhevm/solidity`、Zama SDK、Zama docs 是否已经提供目标 mainnet 的 host contracts、gateway、relayer 与审计状态。若依赖源码或官方文档没有 mainnet 配置，不要硬编码 Sepolia/local 地址冒充 mainnet。

`.env.mainnet` 示例，不包含 private key：

```bash
MAINNET_RPC_URL=https://...
ETHERSCAN_API_KEY=...
DEPLOYER_ACCOUNT=zama-mainnet-deployer
OWNER=0x...
```

部署：

```bash
source .env.mainnet

forge script script/DeployConfidentialVault.s.sol:DeployConfidentialVault \
  --rpc-url "$MAINNET_RPC_URL" \
  --account "$DEPLOYER_ACCOUNT" \
  --broadcast \
  --verify \
  --etherscan-api-key "$ETHERSCAN_API_KEY"
```

Mainnet 注意事项：

- 优先使用硬件钱包、multisig 或受控 signer 流程；如果使用 keystore，使用专门部署账户并最小化余额。
- 不要把生产 private key 提交到 `.env`、脚本、shell history 或 CI log。
- 在 mainnet fork 上演练部署 nonce、constructor 参数、verification、权限初始化和 pause/owner 逻辑。
- FHEVM 逻辑发布前必须覆盖 ACL 错误路径：错误 user 不能 decrypt、缺少 `allowThis` 会失败、未 public 标记的 handle 不能 public decrypt。
- 不要部署 `forge-fhevm` cleartext host stack 到 Ethereum mainnet；它是开发工具，且 cleartext executor 不提供生产隐私。
- 对任何 `FHE.makePubliclyDecryptable` 调用做产品级审查；mainnet 上 public decrypt 是永久公开。

## 远程 cleartext host stack 仅用于私有开发链

`forge-fhevm/deploy.sh` 的用途是把 cleartext FHEVM host contracts 部署到 testnets/private chains，并改写 `FHEVMHostAddresses.sol`。只有在你明确要维护自己的 cleartext 开发网络时才使用它。接入 Zama 官方 Sepolia/mainnet 时，部署你的 dApp 合约即可。

如果确实要跑 `deploy.sh`，按当前安装的 `forge-fhevm/deploy.sh` 读取它需要的变量，但不要把任何 signer private key 写进仓库内 `.env`。这类脚本通常还涉及 KMS/coprocessor mock signer；它们也只应该用于 disposable 私有开发链或安全 secret manager 管理的临时环境。
