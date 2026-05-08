---
name: zama-hardhat-contract-dev
description: 使用 Hardhat 开发、测试、部署 Zama FHEVM confidential contracts 时使用。适用于 fhevm-hardhat-template、@fhevm/hardhat-plugin、Hardhat mock、TypeScript 测试、encrypted input、user/public decrypt、ACL、ERC7984 confidential token、Hardhat task、localhost/Sepolia/mainnet 部署和合约验证。
---

# Zama Hardhat Contract Dev

`@fhevm/hardhat-plugin` 是 Zama 的 Hardhat-native FHEVM 开发插件。它扩展 Hardhat Runtime Environment，提供 `hre.fhevm` / `import { fhevm } from "hardhat"`，用于生成 encrypted input、执行 user/public decrypt、初始化 CLI task 环境，并在 Hardhat mock 网络里部署 FHEVM host contracts。

合约本身仍按 `@fhevm/solidity` 的方式开发：使用 encrypted types、`FHE.fromExternal`、`FHE.add/select/...`、`FHE.allowThis`、`FHE.allow`、`FHE.makePubliclyDecryptable` 等模式。

## 先读哪个 reference

- 新建或修复 Hardhat 项目：读 `references/hardhat-project.md`
- 查询 Hardhat FHEVM API：读 `references/api/README.md`
- 写部署脚本：读 `references/deploy.md`
- 写测试前的总览：读 `references/testing/README.md`
- encrypted input 测试：读 `references/testing/encrypt.md`
- decrypt / ACL 测试：读 `references/testing/decrypt-acl.md`
- public decrypt 测试：读 `references/testing/public-decrypt.md`
- Sepolia 端到端测试：读 `references/testing/sepolia.md`
- ERC7984 token 测试：读 `references/testing/erc7984.md`

## 使用原则

- 先检查项目实际 `package.json`、`hardhat.config.ts`、`types/` 和 lockfile，再套用 reference 示例。
- 模板当前使用 Node `>=20`、Solidity `0.8.27`、`evmVersion = "cancun"`；具体项目以当前配置为准。
- `hardhat.config.ts` 必须 import `@fhevm/hardhat-plugin`，否则 `fhevm` HRE API 不存在。
- TypeScript 测试里优先从 `hardhat` 导入 `ethers, fhevm`，从 `@fhevm/hardhat-plugin` 导入 `FhevmType`。
- `fhevm.isMock` 为 true 的 mock 测试可以使用本地 decrypt helper；Sepolia/mainnet 是真实 FHEVM 环境，测试应独立分组。
- Hardhat task 中必须先调用 `await fhevm.initializeCLIApi()`，普通 `hardhat test` 不需要手动调用。
- 部署不要把 private key 写进 `.env`；live networks（Sepolia/mainnet）也不能 fallback 到 Hardhat 默认测试 mnemonic、占位 RPC 或空 signer。缺少 signer/RPC 时必须 fail fast，并给出需要设置的 Hardhat vars 或 secret manager 配置。
- 本地 `hardhat` / `localhost` 可以使用公开测试 mnemonic；Sepolia/mainnet 必须使用独立的 network-specific signer，例如 `SEPOLIA_MNEMONIC`、硬件钱包、multisig 或受控 secret manager。Hardhat vars 是本地明文存储，不适合高价值生产密钥。

## 上游依据

本 skill 的 API 与部署说明以当前项目安装的 `@fhevm/hardhat-plugin`、`@fhevm/mock-utils`、`@fhevm/solidity` 和 `zama-ai/fhevm-hardhat-template` 为准。若 reference 与项目依赖不一致，以项目源码和 TypeScript 类型定义为准。
