---
name: zama-foundry-forge-fhevm
description: 使用 Foundry 和 forge-fhevm 开发、测试、部署 Zama FHEVM confidential contracts 时使用。适用于 FhevmTest、forge test、Foundry 项目初始化、Solidity 0.8.27、Cancun EVM、encrypted input、direct/public/user decrypt、ACL、ERC7984 confidential token、fuzz、local/Sepolia/mainnet 部署。
---

# Zama Foundry forge-fhevm

`forge-fhevm` 是 Zama 的 Foundry-native FHEVM 测试与本地开发工具。它让 Forge 测试继承 `FhevmTest` 后，在测试环境里部署真实 fhEVM host contracts，包括 `FHEVMExecutor`、`ACL`、`InputVerifier`、`KMSVerifier`，并用本地明文数据库跟踪 encrypted handle，便于在 Foundry 中完成 encrypt、compute、decrypt、assert。

合约本身仍按 `@fhevm/solidity` 的方式开发：使用 encrypted types、`FHE.fromExternal`、`FHE.add/select/...`、`FHE.allowThis`、`FHE.allow`、`FHE.makePubliclyDecryptable` 等模式。

## 先读哪个 reference

- 新建或修复 Foundry 项目：读 `references/foundry-project.md`
- 写部署脚本：读 `references/deploy.md`
- 查询 forge-fhevm API：读 `references/api/README.md`
- 写测试前的总览：读 `references/testing/README.md`
- 加密输入测试：读 `references/testing/encrypt.md`
- 解密测试：读 `references/testing/decrypt.md`
- ACL/权限测试：读 `references/testing/acl.md`
- ERC7984 token 测试：读 `references/testing/erc7984.md`
- fuzz、失败路径和排错：读 `references/testing/fuzz-and-errors.md`

## 使用原则

- 先检查当前项目实际安装的 `forge-fhevm/FhevmTest.sol`、`deploy-local.sh`、`deploy.sh`，再套用 reference 示例。
- `forge-fhevm` 当前要求 Solidity `^0.8.27` 和 `evm_version = "cancun"`。
- 不要把 `@fhevm-solidity`、`@encrypted-types` 等 Soldeer 依赖写成 `latest`；先用本 skill 的已验证版本启动，升级时再查询 registry 并同步 `foundry.toml`、`soldeer.lock` 和 `remappings.txt`。
- 覆写 Forge 测试的 `setUp()` 时先调用 `super.setUp()`。
- `FhevmTest.decrypt` 是测试用明文读取，不执行 ACL 检查；涉及权限时必须覆盖 `publicDecrypt` 或 `userDecrypt`。
- 实际部署不要在 `.env` 或脚本中保存 private key；使用 Foundry keystore，脚本用 `vm.startBroadcast()`，命令行用 `forge script --account <name>`。
- 本地 Anvil-only demo 的 deploy wrapper 应显式设置 `LOCAL_STATE_RPC_NAMESPACE=anvil`，避免 `cast client` 探测为空；如果部署脚本写 JSON，必须在 `foundry.toml` 配 `fs_permissions`。
- 本地 cleartext FHEVM stack 只服务开发与测试，不代表生产链隐私部署。

## 上游依据

本 skill 的 API 与部署说明以 `zama-ai/forge-fhevm` 源码和 docs 为准，尤其是 `src/FhevmTest.sol`、`docs/api/*.md`、`docs/guides/*.md`、`deploy-local.sh`、`deploy.sh`。如果上游 API 文档和当前安装源码不一致，以项目实际安装源码为准。
