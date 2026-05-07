# 配置

每个 SDK 实例都需要三个核心部分：relayer runtime、signer 和 storage backend。本文件沿用官方 configuration guide 的结构，并补充 authentication、browser/server 边界、artifact cache、web extension 和清理逻辑。

## 包导出

Core SDK：

| Import path | 用途 |
| --- | --- |
| `@zama-fhe/sdk` | `ZamaSDK`、`RelayerWeb`、网络预设、storage、`Token`、`ReadonlyToken`、builders、errors |
| `@zama-fhe/sdk/node` | `RelayerNode`、worker options、`asyncLocalStorage` |
| `@zama-fhe/sdk/cleartext` | `RelayerCleartext`、`hardhatCleartextConfig`、`hoodiCleartextConfig` |
| `@zama-fhe/sdk/viem` | `ViemSigner` 和 viem helper |
| `@zama-fhe/sdk/ethers` | `EthersSigner` 和 ethers helper |
| `@zama-fhe/sdk/query` | TanStack Query option factories 和 query keys |

React SDK：

| Import path | 用途 |
| --- | --- |
| `@zama-fhe/react-sdk` | `ZamaProvider`、hooks、面向 React 的 re-exports |
| `@zama-fhe/react-sdk/wagmi` | `WagmiSigner` |

尽量从最具体的 export path 导入。常见错误是从 browser 主入口导入 `RelayerNode`，或从非 wagmi 路径导入 `WagmiSigner`。

## 依赖选择

| 项目 | 安装 |
| --- | --- |
| Browser / vanilla TS + viem | `@zama-fhe/sdk viem` |
| Browser / vanilla TS + ethers | `@zama-fhe/sdk ethers` |
| React / wagmi | `@zama-fhe/react-sdk @tanstack/react-query viem wagmi` |
| Node backend | `@zama-fhe/sdk viem` 或 `@zama-fhe/sdk ethers` |

不要盲目升级 SDK 包。先读项目 lockfile，再确认 Node、bundler 和 wallet library 是否兼容。

## 网络预设

SDK 暴露的常用 preset：

| Preset | Chain ID | 典型用途 |
| --- | --- | --- |
| `MainnetConfig` | `1` | Ethereum Mainnet |
| `SepoliaConfig` | `11155111` | Sepolia testnet |
| `HardhatConfig` | `31337` | local Hardhat node |

Preset 提供 SDK 所需的合约和网络元数据，包括 chain id、relayer URL、gateway address、ACL address、KMS verifier address。用 preset 作为基线，再覆盖项目自己的 RPC/proxy URL。

```ts
const transports = {
  [SepoliaConfig.chainId]: {
    ...SepoliaConfig,
    network: process.env.NEXT_PUBLIC_SEPOLIA_RPC_URL!,
    relayerUrl: "/api/relayer/11155111",
  },
};
```

## 浏览器 Transport

Browser 代码在需要 relayer authentication 时应配置 proxy URL：

```ts
const relayer = new RelayerWeb({
  getChainId: () => signer.getChainId(),
  transports: {
    [SepoliaConfig.chainId]: {
      ...SepoliaConfig,
      network: "https://ethereum-sepolia-rpc.publicnode.com",
      relayerUrl: "/api/relayer/11155111",
    },
  },
});
```

proxy 负责把请求转发到实际 relayer endpoint，并在服务端注入私有 credentials。

## Node Transport

服务端代码可以读取私有环境变量：

```ts
const relayer = new RelayerNode({
  getChainId: () => signer.getChainId(),
  transports: {
    [SepoliaConfig.chainId]: {
      ...SepoliaConfig,
      network: process.env.SEPOLIA_RPC_URL!,
      auth: { __type: "ApiKeyHeader", value: process.env.RELAYER_API_KEY! },
    },
  },
});
```

这种写法只用于服务端。RPC URL、relayer URL、private key、mnemonic、API key 都应按环境管理。

## 认证

官方文档描述了两种认证策略：

| 策略 | 使用场景 | secret 位置 |
| --- | --- | --- |
| Backend proxy | browser apps 和 dApps | 只在服务端 |
| Direct API key | Node scripts、backend services、prototyping | transport `auth` 字段 |

Browser app 不应在前端 runtime config 中包含 `auth`。把 `relayerUrl` 指向同源或可信后端 endpoint：

```ts
const relayer = new RelayerWeb({
  getChainId: () => signer.getChainId(),
  transports: {
    [SepoliaConfig.chainId]: {
      ...SepoliaConfig,
      relayerUrl: "https://your-app.com/api/relayer/11155111",
      network: "https://sepolia.infura.io/v3/YOUR_KEY",
    },
  },
});
```

服务端代码可以传：

```ts
auth: { __type: "ApiKeyHeader", value: process.env.RELAYER_API_KEY! }
```

支持的 auth shape：

| 方法 | 形态 | Header 或 transport 行为 |
| --- | --- | --- |
| `ApiKeyHeader` | `{ __type: "ApiKeyHeader", value: "key" }` | 发送 `x-api-key` |
| `ApiKeyCookie` | `{ __type: "ApiKeyCookie", value: "key" }` | 设置 cookie |
| `BearerToken` | `{ __type: "BearerToken", token: "jwt" }` | 发送 `Authorization: Bearer ...` |

使用 browser proxy 时，如果应用有登录态或 state-changing proxy 行为，应加入 CSRF protection。

## Relayer API Key 获取与托管方式

上游文档把 relayer 接入分成两类：

| 方式 | 适用场景 | 注意 |
| --- | --- | --- |
| Zama-hosted Relayer | mainnet/testnet 应用，不想自运维 relayer | 需要申请 API key，并按用量/协议计费 |
| Self-hosted Relayer | 对运维、计费、gateway wallet 有独立要求 | 需要自己部署、监控和维护 relayer |

拿到 Zama-hosted key 后，仍然按上一节选择 browser proxy 或 server-side direct key。不要把申请到的 key 放进 `NEXT_PUBLIC_`、`VITE_` 或任何前端 bundle。

如果怀疑 key 泄漏，应停止使用该 key，轮换配置，并联系 Zama support。

## 多链配置

每条支持的链提供一个 transport：

```ts
const relayer = new RelayerWeb({
  getChainId: () => signer.getChainId(),
  transports: {
    [SepoliaConfig.chainId]: {
      ...SepoliaConfig,
      network: sepoliaRpcUrl,
      relayerUrl: "/api/relayer/11155111",
    },
    [MainnetConfig.chainId]: {
      ...MainnetConfig,
      network: mainnetRpcUrl,
      relayerUrl: "/api/relayer/1",
    },
  },
});
```

UI 中要显式展示 chain selection。不要跨链静默复用 handles、credentials 或 contract addresses。

## Signer 选择

| Signer | Import | 用途 |
| --- | --- | --- |
| `WagmiSigner` | `@zama-fhe/react-sdk/wagmi` | 使用 wagmi 的 React app |
| `ViemSigner` | `@zama-fhe/sdk/viem` | viem wallet/public clients |
| `EthersSigner` | `@zama-fhe/sdk/ethers` | ethers v6 signer/provider |
| 自定义 `GenericSigner` | 项目代码 | smart wallet 或自定义 transport |

Signer 需要提供 chain id、account address、typed-data signatures、contract reads/writes、transaction receipt waiting、block timestamp reads。如果 signer 能发出 account/chain 变化事件，实现 `subscribe`，让 SDK 状态可以安全重置。

## Storage 选择

| Storage | 导入 | 用途 |
| --- | --- | --- |
| `indexedDBStorage` | `@zama-fhe/sdk` | browser 持久化 keypair/session/decrypt cache |
| `memoryStorage` | `@zama-fhe/sdk` | scripts、tests、短生命周期 session |
| `chromeSessionStorage` | `@zama-fhe/sdk` | Chrome extension session storage |
| `asyncLocalStorage` | `@zama-fhe/sdk/node` | Node request-scoped storage |

Browser app 通常使用 `indexedDBStorage`。CLI task 通常使用 `memoryStorage`。多用户服务器需要 request isolation。

## FHE Artifact Cache

`RelayerWeb` 和 `RelayerNode` 会缓存多 MB 的 FHE public keys 和参数。

| Runtime | 默认 cache 行为 |
| --- | --- |
| `RelayerWeb` | IndexedDB，跨 reload 持久化 |
| `RelayerNode` | 内存，进程重启后丢失 |

cache 会定期重新验证 artifact source。可通过以下选项调整：

```ts
const relayer = new RelayerWeb({
  getChainId: () => signer.getChainId(),
  fheArtifactStorage,
  fheArtifactCacheTTL,
  transports,
});
```

只有当项目明确需要自定义持久化或隔离策略时，才使用 custom artifact storage。

## Web Extension

Chrome MV3 extension 可能需要单独的 session storage，因为 service worker 可能随时被终止：

```ts
import {
  ZamaSDK,
  RelayerWeb,
  indexedDBStorage,
  chromeSessionStorage,
  SepoliaConfig,
} from "@zama-fhe/sdk";

const sdk = new ZamaSDK({
  relayer,
  signer,
  storage: indexedDBStorage,
  sessionStorage: chromeSessionStorage,
});
```

extension manifest 需要 `storage` permission。

## Registry 覆盖配置

如果某条链没有 SDK 默认 registry address，显式提供：

```ts
const sdk = new ZamaSDK({
  relayer,
  signer,
  storage,
  registryAddresses: {
    [31337]: "0xRegistry",
  },
});
```

这会影响 confidential token wrapper discovery 和 registry helpers。

## SSR 和 Client 边界

Next.js 等框架的规则：

- 使用 `@zama-fhe/react-sdk` 的组件必须是 client component
- 不要在 server component 中 import hooks 或 `ZamaProvider`
- 不要在 server-only module 里创建 `RelayerWeb`
- 避免在 server/client 共享模块中实例化 browser SDK 代码
- provider wiring 放在专门的 `"use client"` 文件里

如果页面同时需要 server data 和 SDK 交互，把它拆成 server shell 和 client child component。

## 生命周期和清理

使用：

```ts
await sdk.revokeSession();
sdk.dispose();
sdk.terminate();
```

- `revokeSession` 清理 session signature 和当前 requester 的 decrypt cache。
- `dispose` 移除 signer lifecycle subscriptions。
- `terminate` 还会关闭 relayer runtime worker 或 pool。

React `ZamaProvider` unmount 时会 dispose 它创建的 SDK。如果 relayer instance 是调用方在 provider 外部创建并持有的，是否 terminate 需要调用方单独决定。

## TTLs 和事件

有意识地配置 decrypt keypair 和 session signature 生命周期。源码默认值如下：

| 选项 | 默认值 | 边界 |
| --- | --- | --- |
| `keypairTTL` | `2592000` 秒，30 天 | 必须大于 0；超过 365 天会被 capped |
| `sessionTTL` | `2592000` 秒，30 天 | `0` 表示每次都签名；也支持 `"infinite"` |
| `registryTTL` | `86400` 秒，24 小时 | 影响 registry lookup cache |

```ts
const sdk = new ZamaSDK({
  relayer,
  signer,
  storage,
  keypairTTL: 604800,
  sessionTTL: 3600,
  onEvent: ({ type, ...event }) => {
    console.debug(`[zama] ${type}`, event);
  },
});
```

设置 `sessionTTL: 0` 会禁用 session caching，所有需要 session signature 的操作都会触发钱包签名。只有产品明确需要这种行为时才这样做。

设置 `sessionTTL: "infinite"` 会让 session signature 不主动过期。它适合受控环境或 extension/service 场景，但 keypair 仍然受 `keypairTTL` 约束。

如果数值型 `sessionTTL` 大于 `keypairTTL`，SDK 会把它 clamp 到 `keypairTTL`，避免 `isAllowed()` 仍为 true 但 keypair 已经过期。

更完整的 session/security 细节见 `session-security.md`。
