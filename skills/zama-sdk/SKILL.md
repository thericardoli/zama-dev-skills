---
name: zama-sdk
description: 使用 Zama SDK 构建 FHEVM dApp、脚本、后端或 React 前端时使用。适用于 @zama-fhe/sdk、@zama-fhe/react-sdk、RelayerWeb、RelayerNode、RelayerCleartext、ZamaSDK、ZamaProvider、WagmiSigner/ViemSigner/EthersSigner、encrypted input、user decrypt、public decrypt、delegated decrypt、ERC7984 confidential token、wagmi/viem/ethers 集成。
---

# Zama SDK

`@zama-fhe/sdk` 和 `@zama-fhe/react-sdk` 是 Zama Protocol 的 TypeScript SDK，用于在应用层接入 FHEVM / confidential smart contracts。它覆盖浏览器 dApp、React/wagmi 前端、Node.js 脚本或后端、本地 cleartext 开发，以及 ERC7984 confidential token 的常见产品流程。

官方 GitHub 仓库：`https://github.com/zama-ai/sdk`

## 包含内容

这个 skill 主要整理这些主题：

- SDK 初始化：relayer runtime、signer、storage、network transport。
- React 集成：`ZamaProvider`、wagmi、TanStack Query hooks、Next.js client/server 边界。
- 自定义 FHE 合约：encrypted input、input proof、contract write、user decrypt、public decrypt。
- ERC7984 token：shield、confidential balance、confidential transfer、operator approval、unshield、registry discovery。
- Node 和本地开发：`RelayerNode`、request-scoped storage、proxy、`RelayerCleartext`。
- 产品集成：activity feed、wallet/exchange 展示、delegated decryption、typed errors 和排障。

## 如何使用

1. 先判断你做的是 ERC7984 token flow，还是自定义 FHE 合约 flow。
2. 再判断运行环境：React/browser、vanilla TypeScript、Node 后端/脚本，或本地 cleartext。
3. 按环境选 reference，先搭好 SDK/Provider，再实现具体业务动作。
4. API 名称或参数不确定时，看 `references/api-reference.md`，再到项目安装后的 `node_modules/@zama-fhe/*` 查类型。

## Reference 索引

| 文件 | 何时查看 |
| --- | --- |
| `references/getting-started.md` | 新项目第一次接入；需要快速理解 SDK 能做什么、安装哪些包、最小 React/Node/local 示例怎么写。 |
| `references/configuration.md` | 配 relayer、network preset、API key、backend proxy、signer、storage、registry override、artifact cache。 |
| `references/session-security.md` | 处理钱包签名弹窗、decrypt credentials、TTL、session lifecycle、浏览器安全、API key 边界。 |
| `references/custom-contracts.md` | 目标合约不是 ERC7984 token，而是 auction、vault、counter、voting 等自定义 encrypted state。 |
| `references/react-wagmi-nextjs.md` | React、wagmi 或 Next.js 项目；需要 provider 栈、hooks、授权 gate、SSR/client 边界。 |
| `references/node-and-local.md` | Node 脚本、后端服务、server-side relayer auth、request isolation、本地 cleartext runtime。 |
| `references/token-workflows.md` | ERC7984 confidential token 的 shield、balance、transfer、approve、unshield、registry 和 token hooks。 |
| `references/activity-wallet-integration.md` | 钱包、portfolio、交易所或 dashboard；需要 activity feed、wrapper discovery、operator/delegation UX。 |
| `references/errors-events.md` | 需要 typed error handling、`matchZamaError`、SDK lifecycle events、event decoders、activity helpers。 |
| `references/api-reference.md` | 查询 import path、class/hook 名称、参数形态、query factory 和本地类型入口。 |
| `references/troubleshooting.md` | 出现 import、worker/WASM、relayer auth、decrypt、token balance、registry、cleartext 等问题时排查。 |

## 工作流程

1. 先读目标项目的 `package.json`、lockfile、Node 版本、framework 和 wallet stack。
2. 按上面的索引选择最相关的 reference，不需要从头读完整套文档。
3. 按环境选 runtime：browser/React 用 `RelayerWeb`，Node 后端/脚本用 `RelayerNode`，本地 cleartext 用 `RelayerCleartext`。
4. 新项目先查询 pnpm registry 上真实可用的 `@zama-fhe/sdk` / `@zama-fhe/react-sdk` 版本，不要照写陈旧版本号。
5. 按 wallet stack 选 signer：wagmi 优先尝试 `WagmiSigner`；如果当前 SDK/wagmi 组合构建失败，立即改用本 skill 的 custom `GenericSigner` fallback；viem 用 `ViemSigner`，ethers 用 `EthersSigner`。
6. 按数据生命周期选 storage：browser 用 `indexedDBStorage`，测试/一次性脚本用 `memoryStorage`，Node 多请求隔离用 `asyncLocalStorage`。
7. 先搭 SDK/Provider，再实现业务流程；不要在同一步里混合网络配置、钱包状态、合约 ABI 和 UI state。
8. token 任务按 shield、balance、transfer、operator approval、unshield、activity feed 拆；自定义合约任务走 encrypt/decrypt 文档。
9. 最后检查 contract address、user address、chain id、handle、input proof、ACL、API key 暴露、session TTL、browser security headers 和 SSR 边界。
