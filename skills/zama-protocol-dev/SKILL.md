---
name: zama-protocol-dev
description: Zama Protocol 开发任务的总入口和 skill 索引。用于在 Zama FHEVM Solidity、Hardhat、Foundry、Zama SDK、React/wagmi/viem 和安全审计等多个 skill 之间选择正确路径，尤其适合跨栈任务或用户没有明确指定框架时。
---

# Zama Protocol Dev

## 简介

本 skill 是 Zama Protocol 开发的总入口。它不提供具体 API 细节，只负责帮助 agent 判断当前任务应该加载哪些 Zama skill，以及按什么顺序读取。

使用原则：

- 不要一次性加载所有 Zama skill。
- 先识别任务所在层：Solidity core、Hardhat、Foundry、前端/SDK、安全审计。
- 单层任务只加载对应 skill。
- 跨栈任务按 workflow 逐层加载，先合约 core，再框架，再前端或审计。

## Skill 索引

- `zama-fhevm-solidity-core`：FHEVM Solidity 合约核心。类型、`FHE` API、encrypted input、ACL、解密、ERC7984 合约模式。
- `zama-hardhat-contract-dev`：Hardhat 项目开发、测试、部署。`@fhevm/hardhat-plugin`、mock、localhost、Sepolia、TypeScript 测试。
- `zama-foundry-forge-fhevm`：Foundry/forge-fhevm 项目开发和测试。`FhevmTest`、Forge tests、fuzz、本地 cleartext stack。
- `zama-sdk`：新版 Zama TypeScript/React SDK。`@zama-fhe/sdk`、`@zama-fhe/react-sdk`、RelayerWeb/Node/Cleartext、ZamaSDK、ZamaProvider、wagmi/viem/ethers、encrypted input、decrypt、ERC7984 token，并替代旧 relayer/react-wagmi skill。
- `zama-fhevm-security-review`：FHEVM 安全审计。ACL、input proof、public decrypt、replay、reorg、overflow、mock/生产差异。

## References

- [references/skill-map.md](references/skill-map.md)：每个 Zama skill 的职责、边界和选择规则。
- [references/workflow-map.md](references/workflow-map.md)：常见任务的 skill 读取顺序。

## 默认判断

如果用户只说“Zama 合约”或“fhevm 合约”，先用 `zama-fhevm-solidity-core`。如果用户明确提到 Hardhat、Foundry、React、SDK、relayer、审计，则加载对应 skill。跨栈任务只加载完成当前步骤所需的最小集合。
