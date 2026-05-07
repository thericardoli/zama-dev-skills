---
name: zama-fhevm-solidity-core
description: 使用 Zama FHEVM Solidity 编写、修改或解释 confidential smart contracts 时使用。适用于 @fhevm/solidity、FHE、euint/externalEuint、ACL、加密输入、解密流程、ZamaConfig 和 ERC7984 集成。
---

# Zama FHEVM Solidity Core

## 简介

本 skill 是 Zama FHEVM Solidity 开发的总入口，用于帮助 agent 理解和实现基于 `@fhevm/solidity` 的 confidential smart contracts。

FHEVM Solidity 的核心任务是：在 Solidity 中声明 encrypted 类型，验证链下提交的 encrypted input，在密文域中计算，通过 ACL 控制 handle 的后续使用和解密权限，并在合适场景下支持 user decrypt 或 public decrypt。

## 使用原则

- 先读项目当前依赖和配置，再决定 API 写法。
- 不确定 Zama Protocol、官方仓库或整体架构时，先读 overview。
- 不确定类型或函数签名时，先读 api，并以当前项目安装的源码为准。
- 具体开发任务只读取对应 pattern 文件，避免一次性加载所有 reference。

## References

- [references/overview.md](references/overview.md)：介绍 Zama Protocol、fhevm-solidity 解决的问题、整体架构和官方仓库入口。
- [references/api.md](references/api.md)：记录常用 encrypted 类型、`FHE` API、ACL API、解密 API、配置类型和调试入口。
- [references/patterns/encryption.md](references/patterns/encryption.md)：外部 encrypted input、`FHE.fromExternal`、Hardhat/Foundry 加密输入测试模式。
- [references/patterns/decryption.md](references/patterns/decryption.md)：user decrypt、public decrypt、链上签名验证和常见解密错误。
- [references/patterns/acl.md](references/patterns/acl.md)：`allowThis`、`allow`、`allowTransient`、public decrypt 权限和多用户权限传播。
- [references/patterns/operations.md](references/patterns/operations.md)：算术、比较、位运算、类型选择、scalar 操作和 overflow-safe 更新。
- [references/patterns/branching.md](references/patterns/branching.md)：`FHE.select`、encrypted condition、固定轮数循环、异步公开分支和错误处理。
- [references/patterns/randomness.md](references/patterns/randomness.md)：`FHE.randE*`、bounded random、交易限制、ACL 和游戏/抽签模式。
- [references/patterns/reorgs.md](references/patterns/reorgs.md)：高价值 secret 的两阶段 ACL 授权和 reorg 风险处理。
- [references/patterns/erc7984.md](references/patterns/erc7984.md)：OpenZeppelin ERC7984 confidential token 的最小集成、转账、余额读取和扩展注意事项。

## 最小安全提醒

不要把普通 `bytes32` 当作已验证 encrypted input；不要忘记为新 handle 设置 ACL；不要为了方便调试把敏感状态设置为 publicly decryptable。
