# 入门指南

这是为项目接入 Zama SDK 时优先阅读的文档。先理解 SDK 能做什么，再选择包和运行环境，最后按 React、vanilla TypeScript、Node.js 或本地开发给出最小可运行骨架。

## SDK 做什么

Zama SDK 是 confidential smart contracts 的 TypeScript 应用层。在典型项目里，它负责：

- 通过 relayer runtime 获取公开加密材料
- 在合约调用前加密 external input
- 为 Solidity 中的 `externalEuintX`、`externalEbool`、`externalEaddress` 生成 encrypted handles 和 input proof
- 管理由钱包签名授权的 decrypt credentials
- 解密用户被 ACL 授权读取的 handles
- 请求 public decrypt 结果和 proof
- 把 ERC7984 confidential token 的 shield、transfer、unshield、balance 流程封装成高层 API

Solidity 合约仍然定义隐私策略。SDK 代码必须匹配合约 ABI、目标地址、ACL 设计和 decrypt 模型。

## 官方功能模型

官方 SDK 文档把主要功能归纳为三类：

| 功能 | 含义 |
| --- | --- |
| Shield 与 unshield | 把公开 ERC20 token 转换成 encrypted token，或再转回公开 ERC20 |
| Confidential transfer | 在客户端加密转账金额，再提交链上交易 |
| React hooks | 基于 TanStack Query 的 hooks，带 cached decryption 和自动 cache invalidation |

ERC7984 token 项目优先使用高层 token API 和 hooks。非 token 合约再读 `custom-contracts.md`，使用低层 encrypt/decrypt 流程。

## 两个包

| 包 | 使用场景 |
| --- | --- |
| `@zama-fhe/sdk` | vanilla TypeScript、Node.js、CLI 脚本或非 React 框架 |
| `@zama-fhe/react-sdk` | React 应用；包含 provider/hooks，并 re-export 大多数 core SDK 符号 |

Signer adapter 仍从子路径导入，例如 `@zama-fhe/sdk/viem`、`@zama-fhe/sdk/ethers`、`@zama-fhe/react-sdk/wagmi`。

## 项目形态

| 项目形态 | 使用 |
| --- | --- |
| React / wagmi 前端 | `@zama-fhe/react-sdk`、`ZamaProvider`、`WagmiSigner`、React hooks |
| Browser / vanilla TypeScript | `@zama-fhe/sdk`、`RelayerWeb`、`ZamaSDK`、`ViemSigner` 或自定义 signer |
| Node 脚本或后端 | `@zama-fhe/sdk`、`@zama-fhe/sdk/node`、`RelayerNode` |
| 本地 cleartext 应用 | `@zama-fhe/sdk/cleartext`、`RelayerCleartext` |
| ERC7984 confidential token UI | `Token`、`ReadonlyToken`、token hooks |
| 自定义 encrypted 应用 | `relayer.encrypt`、contract write、`sdk.userDecrypt`、`sdk.publicDecrypt` |

## 推荐项目结构

React/wagmi 应用：

```text
src/
  app/
    providers.tsx          # WagmiProvider、QueryClientProvider、ZamaProvider
  lib/
    zama/
      config.ts            # chains、transport config、registry overrides
      sdk.ts               # 如有需要，放 relayer/signer helper
      contracts.ts         # addresses 和 ABI imports
      conversions.ts       # bytesToHex、handle guards、unit helpers
  features/
    confidential-token/
      hooks.ts             # 面向产品 UI 组合 token hooks
      components.tsx
    custom-contract/
      actions.ts           # encrypt + write + decrypt 编排
```

Node 后端：

```text
src/
  zama/
    config.ts              # chain ids、RPC URLs、私有 env 读取
    signer.ts              # 创建 ViemSigner 或 EthersSigner
    sdk.ts                 # ZamaSDK + RelayerNode factory
    proxy.ts               # 可选 browser-to-relayer proxy
    jobs.ts                # public decrypt 或监控任务
```

把合约 ABI/address 与 SDK 创建逻辑分开。这样更容易检查切链、测试和前后端边界。

## 安装

React / wagmi：

```bash
pnpm add @zama-fhe/react-sdk @tanstack/react-query wagmi viem
```

使用 viem 的 vanilla TypeScript 或 Node.js：

```bash
pnpm add @zama-fhe/sdk viem
```

使用 ethers 的 vanilla TypeScript 或 Node.js：

```bash
pnpm add @zama-fhe/sdk ethers
```

在 Node 中运行 SDK 代码的项目使用 Node.js `>=22`。

## 认证规则

relayer 请求需要 API key。Browser 应用应通过后端 proxy 转发 relayer 请求，让 key 留在服务端：

```ts
relayerUrl: "https://your-app.com/api/relayer/11155111"
```

服务端脚本和后端服务可以在 transport config 里直接传 credentials：

```ts
auth: { __type: "ApiKeyHeader", value: process.env.RELAYER_API_KEY! }
```

前端框架里只暴露公开变量。Next.js 使用 `NEXT_PUBLIC_`，Vite 使用 `VITE_`。

## Runtime 组成

每个接入都由四个部分组合：

| 部分 | 责任 | 常用选择 |
| --- | --- | --- |
| Relayer runtime | 加密材料、decrypt 请求、proof 请求 | `RelayerWeb`、`RelayerNode`、`RelayerCleartext` |
| Signer | chain id、account、typed-data signatures、contract calls | `WagmiSigner`、`ViemSigner`、`EthersSigner` |
| Storage | keypair、session signature、decrypt cache | `indexedDBStorage`、`memoryStorage`、`asyncLocalStorage` |
| SDK facade | credentials、cache、token registry、token objects | `ZamaSDK`、`ZamaProvider` |

## 最小 Browser SDK

```ts
import {
  ZamaSDK,
  RelayerWeb,
  SepoliaConfig,
  indexedDBStorage,
} from "@zama-fhe/sdk";
import { ViemSigner } from "@zama-fhe/sdk/viem";

const signer = new ViemSigner({ walletClient, publicClient });

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

export const sdk = new ZamaSDK({
  relayer,
  signer,
  storage: indexedDBStorage,
});
```

Browser 代码在需要 relayer credentials 时应使用服务端 proxy URL。不要把私有 API key 放进前端 bundle。

## 第一笔 confidential transfer

官方 30 秒流程以 token 为中心：

```ts
const token = sdk.createToken("0xYourEncryptedERC20");

await token.shield(1000n);
const balance = await token.balanceOf();
await token.confidentialTransfer("0xRecipient", 500n);
await token.unshield(500n);
```

ERC7984 confidential token 应用优先走这条路径。只有合约本身定义了自定义 encrypted 参数时，才读 `custom-contracts.md`。

## 最小 React Provider

```tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  ZamaProvider,
  RelayerWeb,
  SepoliaConfig,
  indexedDBStorage,
} from "@zama-fhe/react-sdk";
import { WagmiSigner } from "@zama-fhe/react-sdk/wagmi";
import { WagmiProvider } from "wagmi";

const queryClient = new QueryClient();
const signer = new WagmiSigner({ config: wagmiConfig });

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

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={queryClient}>
        <ZamaProvider relayer={relayer} signer={signer} storage={indexedDBStorage}>
          {children}
        </ZamaProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}
```

`ZamaProvider` 必须位于 `QueryClientProvider` 之下。Next.js 中这个文件必须是 client-only。

## 最小 React Token 页面

```tsx
import { type FormEvent } from "react";
import { useAccount, useConnect, useDisconnect } from "wagmi";
import { injected } from "wagmi/connectors";
import {
  useConfidentialBalance,
  useConfidentialTransfer,
  useMetadata,
  useShield,
} from "@zama-fhe/react-sdk";

function MyTokenPage() {
  const tokenAddress = "0xYourEncryptedERC20" as const;
  const wrapperAddress = "0xYourWrapper" as const;
  const { address, isConnected } = useAccount();
  const { connect } = useConnect();
  const { disconnect } = useDisconnect();

  const { data: meta } = useMetadata(tokenAddress);
  const { data: balance, isLoading } = useConfidentialBalance({ tokenAddress });
  const shield = useShield({ tokenAddress, wrapperAddress });
  const transfer = useConfidentialTransfer({ tokenAddress });

  if (!isConnected) {
    return <button onClick={() => connect({ connector: injected() })}>连接钱包</button>;
  }

  async function handleShield(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const amount = new FormData(e.currentTarget).get("amount") as string;
    await shield.mutateAsync({ amount: BigInt(amount) });
  }

  async function handleTransfer(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    await transfer.mutateAsync({
      to: data.get("to") as `0x${string}`,
      amount: BigInt(data.get("amount") as string),
    });
  }

  return (
    <section>
      <p>已连接：{address}</p>
      {meta && <p>{meta.name} ({meta.symbol})</p>}
      <p>余额：{isLoading ? "解密中..." : balance?.toString()}</p>
      <form onSubmit={handleShield}>
        <input name="amount" type="number" required />
        <button disabled={shield.isPending}>Shield</button>
      </form>
      <form onSubmit={handleTransfer}>
        <input name="to" placeholder="0x..." required />
        <input name="amount" type="number" required />
        <button disabled={transfer.isPending}>私密转账</button>
      </form>
      <button onClick={() => disconnect()}>断开连接</button>
    </section>
  );
}
```

如果 confidential token 合约本身就是 wrapper，可以省略 `wrapperAddress`。多数 wrapped ERC20 项目会有独立 wrapper address，shield、unshield、underlying allowance 和 approve underlying 都应显式传入。

## 最小 Node SDK

```ts
import { ZamaSDK, SepoliaConfig, memoryStorage } from "@zama-fhe/sdk";
import { RelayerNode } from "@zama-fhe/sdk/node";
import { ViemSigner } from "@zama-fhe/sdk/viem";

const signer = new ViemSigner({ walletClient, publicClient });

export const sdk = new ZamaSDK({
  signer,
  storage: memoryStorage,
  relayer: new RelayerNode({
    getChainId: () => signer.getChainId(),
    transports: {
      [SepoliaConfig.chainId]: {
        ...SepoliaConfig,
        network: process.env.SEPOLIA_RPC_URL!,
        auth: { __type: "ApiKeyHeader", value: process.env.RELAYER_API_KEY! },
      },
    },
  }),
});
```

长生命周期服务器不要在多用户之间共享一个 `memoryStorage`。使用 request-scoped storage，或按可信 job 边界创建 SDK 实例。

## FHE Artifact Cache

`RelayerWeb` 和 `RelayerNode` 会缓存大型 FHE public keys 与参数，避免每次启动都重新下载。Browser runtime 默认用 IndexedDB 持久化；Node runtime 默认保存在内存中。可通过 `fheArtifactStorage` 和 `fheArtifactCacheTTL` 调整。

## 最小本地 Cleartext

```ts
import { ZamaSDK, memoryStorage } from "@zama-fhe/sdk";
import {
  RelayerCleartext,
  hardhatCleartextConfig,
} from "@zama-fhe/sdk/cleartext";

const relayer = new RelayerCleartext(hardhatCleartextConfig);
const sdk = new ZamaSDK({ relayer, signer, storage: memoryStorage });
```

Cleartext 模式只用于兼容本地 stack 的开发和测试。不要用于 Sepolia 或 Mainnet 路径。

## 第一次接入检查清单

- 决定是 custom contract flow 还是 ERC7984 token flow。
- 确认 chain id、contract address、user address、ABI 和 network URL。
- 加密时的 `contractAddress` 必须是调用 `FHE.fromExternal` 的合约。
- 合约写入前把 `Uint8Array` handles 和 proof 转为 hex。
- 从合约读回的 handles 通常已经是 `0x...` 字符串，保持原样。
- user decrypt 要受钱包连接、正确链、授权状态 gate。
- 私有 relayer credentials 只放在服务端。
