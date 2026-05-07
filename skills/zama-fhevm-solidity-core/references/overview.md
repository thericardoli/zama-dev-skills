# Zama Protocol 与 fhevm-solidity 概览

## Zama Protocol 是什么

Zama Protocol 是把 Fully Homomorphic Encryption（FHE，全同态加密）接入 EVM 智能合约的协议栈。它允许合约在不解密用户数据的情况下，对加密状态执行计算，例如加密余额、加密投票、加密出价、加密游戏状态和隐私业务规则。

在普通 EVM 中，合约状态和 calldata 默认公开；即使前端对数据做了加密，合约也无法直接对密文做有意义的算术和比较。FHEVM 的目标是让 Solidity 合约可以把 encrypted handles 当作一等值，通过 Zama 的 coprocessor、ACL 和 KMS/relayer 体系完成密文计算、权限控制和受控解密。

## fhevm-solidity 解决什么问题

`@fhevm/solidity` 是合约开发者直接使用的 Solidity 库。它主要解决：

- **类型封装**：提供 `ebool`、`euintXX`、`eaddress`、`externalEuintXX` 等 encrypted 类型。
- **输入验证**：通过 `FHE.fromExternal(input, proof)` 把外部传入的 encrypted input 转成合约内部可计算值。
- **密文计算**：提供 `FHE.add`、`FHE.sub`、`FHE.gt`、`FHE.select` 等 API。
- **权限控制**：通过 `FHE.allowThis`、`FHE.allow`、`FHE.allowTransient`、`FHE.makePubliclyDecryptable` 管理 handle 的使用和解密权限。
- **解密验证**：提供 public decrypt 签名验证、user decrypt 授权、delegation 等能力。
- **网络配置**：通过 `ZamaEthereumConfig` 把合约连接到当前 chain 对应的 FHEVM host contracts。

## 基本架构

一个典型 FHEVM dApp 包含：

- Solidity 合约：使用 `@fhevm/solidity` 定义 encrypted 状态和业务逻辑。
- FHEVM host contracts：ACL、coprocessor/executor、KMS verifier 等协议合约。
- Relayer / SDK：前端或脚本用来生成 encrypted input、发起 decrypt、处理签名和证明。
- 开发框架：Hardhat plugin 或 forge-fhevm 提供 mock、cleartext、本地测试和部署辅助。

## Solidity 合约的基本思路

合约不直接拿到明文用户输入。典型流程是：

1. 用户或前端在链下把明文加密成 encrypted input。
2. 前端把 `externalEuintXX handle` 和 `inputProof` 传给合约。
3. 合约用 `FHE.fromExternal` 验证输入并得到内部 `euintXX`。
4. 合约用 `FHE.*` API 在 encrypted domain 中计算。
5. 合约为新 handle 设置 ACL。
6. 用户通过 user decrypt 读取被授权的值，或业务在合适时做 public decrypt。

## 官方仓库入口

需要确认版本、API 或示例时，优先查询这些官方或核心仓库：

- Zama FHEVM monorepo：`https://github.com/zama-ai/fhevm`
- Solidity library package：`https://www.npmjs.com/package/@fhevm/solidity`
- Hardhat template：`https://github.com/zama-ai/fhevm-hardhat-template`
- Hardhat plugin package：`https://www.npmjs.com/package/@fhevm/hardhat-plugin`
- Foundry testing library：`https://github.com/zama-ai/forge-fhevm`
- Zama SDK：`https://github.com/zama-ai/sdk`
- React template：`https://github.com/zama-ai/fhevm-react-template`
- Mock utilities：`https://github.com/zama-ai/fhevm-mocks`
- OpenZeppelin confidential contracts：`https://github.com/OpenZeppelin/openzeppelin-confidential-contracts`
- Zama Protocol docs：`https://docs.zama.org/protocol`

## 开发时的版本策略

Zama 生态变化快。写代码前先从当前项目读取实际依赖：

```bash
cat package.json
cat foundry.toml
cat remappings.txt
```

需要确认当前发布版本时再查询 npm 或 GitHub：

```bash
npm view @fhevm/solidity version dist-tags --json
npm view @fhevm/hardhat-plugin version dist-tags --json
gh repo view zama-ai/fhevm --json latestRelease,updatedAt,url
```

不要把某个教程里的旧 import、旧 mock 路径或旧 SDK API 直接迁移到新项目。
