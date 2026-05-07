# Hardhat 项目结构

优先参考 `zama-ai/fhevm-hardhat-template`，再按当前项目已有结构调整。

## 目录

```text
contracts/
deploy/
tasks/
test/
types/
hardhat.config.ts
package.json
tsconfig.json
```

常见职责：

- `contracts/`：FHEVM Solidity 合约。
- `deploy/`：`hardhat-deploy` 脚本。
- `tasks/`：交互、加密输入、user decrypt、运维检查。
- `test/`：mock 单元测试和 Sepolia e2e 测试。
- `types/`：TypeChain 输出。

## 关键依赖

模板当前依赖组合：

- `@fhevm/solidity`
- `@fhevm/hardhat-plugin`
- `@fhevm/mock-utils`
- `@zama-fhe/sdk`
- `hardhat`
- `hardhat-deploy`
- `ethers`
- `@nomicfoundation/hardhat-ethers`
- `@typechain/hardhat`
- `@typechain/ethers-v6`

先读 `package.json` 和 lockfile。不要把 npm latest API 直接套到旧项目。

## hardhat.config.ts

必须启用插件：

```ts
import "@fhevm/hardhat-plugin";
import "@nomicfoundation/hardhat-ethers";
import "@nomicfoundation/hardhat-verify";
import "@typechain/hardhat";
import "hardhat-deploy";
import type { HardhatUserConfig } from "hardhat/config";
import { vars } from "hardhat/config";

const MNEMONIC = vars.get("MNEMONIC", "test test test test test test test test test test test junk");
const INFURA_API_KEY = vars.get("INFURA_API_KEY", "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz");

const config: HardhatUserConfig = {
  defaultNetwork: "hardhat",
  namedAccounts: {
    deployer: 0,
  },
  networks: {
    hardhat: {
      accounts: { mnemonic: MNEMONIC },
      chainId: 31337,
    },
    sepolia: {
      accounts: {
        mnemonic: MNEMONIC,
        path: "m/44'/60'/0'/0/",
        count: 10,
      },
      chainId: 11155111,
      url: `https://sepolia.infura.io/v3/${INFURA_API_KEY}`,
    },
  },
  solidity: {
    version: "0.8.27",
    settings: {
      optimizer: { enabled: true, runs: 800 },
      evmVersion: "cancun",
    },
  },
  typechain: {
    outDir: "types",
    target: "ethers-v6",
  },
};

export default config;
```

注意：

- FHEVM 需要 Cancun EVM。
- 模板用 `vars.get("MNEMONIC")`，不是 `.env PRIVATE_KEY`。
- Hardhat vars 降低误提交 `.env` 的风险，但仍是本地明文文件；不要用于高价值生产密钥。
- 如果项目已用 `dotenv`，迁移时把 `process.env.KEY` 改为 `vars.get("KEY")`，并运行 `npx hardhat vars setup`。

## 合约基线

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import {FHE, euint64, externalEuint64} from "@fhevm/solidity/lib/FHE.sol";
import {ZamaEthereumConfig} from "@fhevm/solidity/config/ZamaConfig.sol";

contract ConfidentialVault is ZamaEthereumConfig {
    mapping(address => euint64) private _balances;

    function deposit(externalEuint64 amount, bytes calldata proof) external {
        euint64 value = FHE.fromExternal(amount, proof);
        euint64 next = FHE.add(_balances[msg.sender], value);

        _balances[msg.sender] = next;
        FHE.allowThis(next);
        FHE.allow(next, msg.sender);
    }

    function balanceOf(address user) external view returns (euint64) {
        return _balances[user];
    }
}
```

合约开发细节读 `zama-fhevm-solidity-core`。Hardhat skill 只说明如何配置、测试、部署。

## 常用命令

优先使用项目已有 npm scripts。模板常见命令：

```bash
npm install
npm run compile
npm test
npm run chain
npm run deploy:localhost
npm run deploy:sepolia
npm run verify:sepolia
```

修改合约 ABI 后：

```bash
npm run compile
npm run typechain
```

如果类型还是旧的：

```bash
npm run clean
npm run compile
```
