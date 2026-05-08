---
name: zama-fullstack-dapp
description: 编排完整 Zama FHEVM dApp 时使用，覆盖 Solidity 合约、Hardhat 或 Foundry、本地开发链、Sepolia/mainnet 部署、@zama-fhe/sdk 或 @zama-fhe/react-sdk、React/Node 客户端、ABI/地址 artifact、monorepo 结构和端到端验证。
---

# Zama Fullstack dApp

本 skill 是完整 dApp 的编排层。它不提供具体 API 示例，也不替代框架 skill；它负责告诉 agent 应该去哪里找资料、如何把合约、部署、SDK、前端和可选后端串起来。

## 何时使用

当任务跨越两个或更多层次时使用：

- FHEVM Solidity 合约 + 前端
- 合约部署 + SDK 调用
- local/Sepolia 双网络 dApp
- React/Node 客户端加密输入和解密
- ABI/地址 artifact 同步
- monorepo 模板、README、端到端验证

如果只是写单个合约函数、单个测试或单个 SDK 调用，不需要本 skill，直接使用对应具体 skill。

## 总加载顺序

1. 先读本文件，确定层次边界和工作顺序。
2. 判断合约框架：
   - Foundry/Forge：读 `references/foundry/README.md`。
   - Hardhat：读 `references/hardhat/README.md`。
3. 合约业务逻辑、encrypted types、ACL、decryption 设计：读 `zama-fhevm-solidity-core`。
4. 合约框架、测试、部署：
   - Foundry：读 `zama-foundry-forge-fhevm`。
   - Hardhat：读 `zama-hardhat-contract-dev`。
5. 前端、Node、relayer runtime、signer、storage、encrypted input、user/public decrypt：读 `zama-sdk`。
6. 涉及安全、ACL、public decrypt、replay、mock-vs-production 差异：读 `zama-fhevm-security-review`。

如果用户没有指定框架，先检查仓库结构。空项目中，优先尊重用户偏好；没有偏好时，Foundry 更适合 Forge/本地 cleartext/e2e 快速模板，Hardhat 更适合 TypeScript-first、Hardhat deploy、TypeChain 和 task 工作流。

## 推荐 Monorepo 边界

统一使用 packages 结构：

```text
packages/
├── contract/   # 合约、合约测试、部署脚本、合约 artifacts
├── frontend/   # React/Vite/Next 前端
└── service/    # 可选：relayer proxy、server jobs、Node SDK smoke tests
```

职责边界：

- `packages/contract` 是 canonical ABI/address artifact 来源。
- `packages/frontend` 只消费 ABI/address artifact，不应该成为唯一部署地址来源。
- `packages/service` 只在需要后端 proxy、server-side decrypt、public decrypt finalize job、定时任务或私有 relayer credentials 时添加。
- 根目录脚本只做编排，具体命令下发到对应 package。

## 串联顺序

1. 合约设计
   先用 `zama-fhevm-solidity-core` 明确 encrypted input、handle 生命周期、ACL、user/public decrypt、运算边界。

2. 框架落地
   用 Foundry 或 Hardhat skill 搭建 `packages/contract`，包括依赖、测试、部署脚本和本地/测试网配置。

3. Artifact 设计
   部署脚本把 ABI 和地址写到 `packages/contract/deployments/`，再生成或复制前端消费文件到 `packages/frontend/src/contracts/`。地址必须按 chain id 区分，不能只保留“最近一次部署”。

4. SDK runtime 选择
   用 `zama-sdk` 判断运行环境：
   - browser/frontend：`RelayerWeb`
   - Node/service：`RelayerNode`
   - local cleartext demo：`RelayerCleartext`

5. 前端或 Node 连接合约
   用 `zama-sdk` 的 custom-contracts、React/wagmi、Node/local references 设计：encrypt input -> submit transaction -> read handle -> authorize decrypt -> user/public decrypt。

6. 可选后端
   只有当需要隐藏 relayer API key、提供 proxy、执行 public decrypt finalize、后台监听链上事件或服务端 smoke test 时，才创建 `packages/service`。

7. 验证和 README
   README 必须把 install、local、Sepolia、frontend、service、test/build 和 required secrets 讲清楚。不能只说“配置 env 后运行”。

## 必须守住的集成点

- `sdk.relayer.encrypt` 的 `contractAddress` 必须是合约中实际调用 `FHE.fromExternal` 的地址。
- handles 和 input proof 必须来自同一次 encryption。
- decrypt 时 handle 必须搭配拥有该 handle 的合约地址。
- user decrypt 需要明确授权动作或 gate，不能在 render 阶段自动弹签名。
- account 或 chain 变化时清理旧 handle、旧 decrypted value 和旧 session 假设。
- local、Sepolia、mainnet 地址 artifact 必须按 chain id 区分。
- `.env` 不会被 npm/pnpm script 自动读取；部署命令需要 wrapper 或明确 source。
- browser 不能接收私有 relayer API key；需要 key 时通过 `packages/service` proxy。
- mock/local cleartext 成功不代表生产 user decrypt 成功。

## 验收门槛

完整 dApp 结束前，至少检查：

- 合约 compile。
- 合约测试覆盖成功路径和 ACL/proof 失败路径。
- 前端 typecheck 和 production build。
- 前端至少有一个非纯工具函数的交互或状态流测试；如果做不到，说明缺口。
- local 部署路径可执行或文档清晰。
- Sepolia 部署命令在缺少 RPC、account、keystore 时能早失败并给清楚提示。
- 可行时执行 SDK smoke path：encrypt input、submit transaction、read handle、decrypt result。
