# React、Wagmi 和 Next.js

本文件适用于 React 前端、Next.js app router 项目、wagmi 钱包集成和 SDK hook 组合。官方 React SDK hooks 基于 TanStack Query，并在适用场景下提供自动 cache invalidation 与 cached decryption。

##  React Reference Map

| 页面 | 用途 |
| --- | --- |
| `ZamaProvider` | 必需 context provider，用于连接 relayer、signer 和 storage |
| `useConfidentialBalance` | 解密并展示 token balance |
| `useShield` | 把公开 ERC20 转为 confidential form |
| `useConfidentialTransfer` | 发送 encrypted token amount |
| `useUnshield` | 把 confidential token 提回公开 ERC20 |
| Query keys | 手动 invalidation 和自定义 query composition |

## Provider 栈

`ZamaProvider` 必须嵌套在 `QueryClientProvider` 之下。wagmi 项目示例：

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
      network: process.env.NEXT_PUBLIC_SEPOLIA_RPC_URL!,
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

对 Vite + React + TypeScript，不要漏掉 React 类型包和 Vite React 插件。一个可用的最小依赖组：

```json
{
  "dependencies": {
    "@rainbow-me/rainbowkit": "^2.2.9",
    "@tanstack/react-query": "^5.90.7",
    "@zama-fhe/react-sdk": "^3.0.0",
    "@zama-fhe/sdk": "^3.0.0",
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
    "viem": "^2.38.5",
    "wagmi": "^2.18.1"
  },
  "devDependencies": {
    "@types/react": "^19.2.0",
    "@types/react-dom": "^19.2.0",
    "@vitejs/plugin-react": "^5.1.0",
    "typescript": "^5.9.0",
    "vite": "^7.2.0"
  }
}
```

版本号是启动点，不是永久真理。新项目要先用 `pnpm view` 查询当前真实版本；如果升级到新的 wagmi/viem 组合，必须跑一次 production build，因为 adapter 兼容问题常在 bundle 阶段暴露。

## Provider 参数

| Prop | 含义 |
| --- | --- |
| `relayer` | `RelayerWeb`、`RelayerNode` 或 `RelayerCleartext` |
| `signer` | `WagmiSigner`、`ViemSigner`、`EthersSigner` 或 custom signer |
| `storage` | keypair 和 decrypt cache storage |
| `sessionStorage` | session signature storage |
| `keypairTTL` | keypair TTL |
| `sessionTTL` | session signature TTL |
| `registryAddresses` | 每条链的 registry override |
| `registryTTL` | registry cache TTL |
| `onEvent` | lifecycle event callback |

组件需要直接访问 SDK 时使用 `useZamaSDK()`：

```tsx
const sdk = useZamaSDK();
const address = await sdk.signer.getAddress();
```

## 自定义合约 Hook Flow

```tsx
import {
  useAllow,
  useEncrypt,
  useIsAllowed,
  useUserDecrypt,
  useZamaSDK,
} from "@zama-fhe/react-sdk";
import { bytesToHex } from "viem";
import { useState } from "react";

const contractAddress = "0xYourContract" as const;

function ConfidentialAction() {
  const sdk = useZamaSDK();
  const encrypt = useEncrypt();
  const allow = useAllow();
  const { data: allowed } = useIsAllowed({
    contractAddresses: [contractAddress],
  });
  const [handles, setHandles] = useState<
    { handle: `0x${string}`; contractAddress: `0x${string}` }[]
  >([]);

  const decrypt = useUserDecrypt(
    { handles },
    { enabled: handles.length > 0 && !!allowed },
  );

  async function submit(amount: bigint) {
    if (!allowed) {
      await allow.mutateAsync([contractAddress]);
    }

    const userAddress = await sdk.signer.getAddress();

    const encrypted = await encrypt.mutateAsync({
      values: [{ type: "euint64", value: amount }],
      contractAddress,
      userAddress,
    });

    await sdk.signer.writeContract({
      address: contractAddress,
      abi,
      functionName: "submit",
      args: [bytesToHex(encrypted.handles[0]!), bytesToHex(encrypted.inputProof)],
    });

    const handle = (await sdk.signer.readContract({
      address: contractAddress,
      abi,
      functionName: "balanceOf",
      args: [userAddress],
    })) as `0x${string}`;

    setHandles([{ handle, contractAddress }]);
  }
}
```

## 授权 Gate

不要因为组件 render 就触发钱包签名：

```tsx
const { data: allowed } = useIsAllowed({
  contractAddresses: [contractAddress],
});

const decrypt = useUserDecrypt(
  { handles: [{ handle, contractAddress }] },
  { enabled: !!allowed && !!handle },
);
```

提供显式授权动作：

```tsx
const allow = useAllow();

async function authorize() {
  await allow.mutateAsync([contractAddress]);
}
```

## Hook 参考

自定义合约 hooks：

| Hook | 用途 |
| --- | --- |
| `useZamaSDK` | 从 context 取 SDK |
| `useEncrypt` | 加密 typed external input |
| `useAllow` | 创建或刷新 user decrypt authorization |
| `useIsAllowed` | 检查 cached authorization |
| `useUserDecrypt` | 解密已授权的 private handles |
| `usePublicDecrypt` | 请求 public handles 的 public decrypt |

Token hooks：

| Hook | 用途 |
| --- | --- |
| `useToken` | read/write token abstraction |
| `useReadonlyToken` | read-only token abstraction |
| `useConfidentialBalance` | 解密单个 balance |
| `useConfidentialBalances` | 批量解密 balances |
| `useShield` | public ERC20 转 confidential token |
| `useConfidentialTransfer` | encrypted transfer |
| `useConfidentialTransferFrom` | operator transfer |
| `useConfidentialApprove` | confidential operator approval |
| `useUnshield` | confidential token 转 public ERC20 |
| `useResumeUnshield` | 恢复 pending unshield |
| `useMetadata` | 读取 token name、symbol、decimals |

Registry 和 discovery hooks：

| Hook | 用途 |
| --- | --- |
| `useWrappersRegistryAddress` | 当前链 registry |
| `useListPairs` | 分页读取 public/confidential pairs |
| `useConfidentialTokenAddress` | public token 转 confidential token |
| `useTokenAddress` | confidential token 转 public token |
| `useWrapperDiscovery` | 发现 wrapper metadata |
| `useIsConfidential` / `useIsWrapper` | interface detection |

Delegation hooks：

| Hook | 用途 |
| --- | --- |
| `useDelegateDecryption` | 授权 delegated decrypt |
| `useRevokeDelegation` | 撤销 delegated decrypt |
| `useDelegationStatus` | 检查 delegation |
| `useDecryptBalanceAs` | 作为 delegate 解密 |
| `useBatchDecryptBalancesAs` | 批量 delegate decrypt |

## UI 状态模型

不要把所有状态都压成一个 `loading`。建议拆成：

- `isConnecting`
- `isWrongChain`
- `isInitializingSDK`
- `isCheckingAuthorization`
- `isAuthorizing`
- `isEncrypting`
- `isWriting`
- `isConfirming`
- `isDecrypting`
- `isRefreshing`
- `lastError`

这样用户能看到明确反馈，也能避免意外签名弹窗。

## Next.js 规则

- provider setup 放在 `"use client"` 文件。
- Server component 可以把 addresses、ABIs 和静态 metadata 传给 client component。
- Client component 负责 wallet connection、SDK hooks、encrypted input 和 decrypt。
- relayer proxy 或任何私有 credentials 走 server route。
- 避免在 server code 会使用的共享模块中 import SDK hooks。

## 浏览器 Worker、WASM 和 Headers

Browser 中的 FHE encryption 使用 Web Worker 和 WASM。

如果显式配置 `RelayerWeb({ threads })`，多线程 WASM 需要 `SharedArrayBuffer`，因此页面必须跨源隔离：

```txt
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

Next.js：

```js
const nextConfig = {
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
          { key: "Cross-Origin-Embedder-Policy", value: "require-corp" },
        ],
      },
    ];
  },
};
```

Vite：

```ts
export default defineConfig({
  server: {
    headers: {
      "Cross-Origin-Opener-Policy": "same-origin",
      "Cross-Origin-Embedder-Policy": "require-corp",
    },
  },
});
```

没有这些 headers 时，SDK 会尝试回退到单线程路径。结果通常是性能下降，而不是功能必然不可用。

如果应用配置了严格 CSP，还要允许 worker 和 WASM：

```txt
Content-Security-Policy: worker-src blob:; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self' https://cdn.zama.org https://your-relayer-proxy.example;
```

## 错误处理模式

建议先写一个本地 error normalizer：

```ts
function getMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  return "未知 Zama SDK 错误";
}
```

需要更丰富的 UI 时，再读 `api-reference.md`，并在已安装项目中查看 `node_modules/@zama-fhe/react-sdk/dist/index.d.ts`、`node_modules/@zama-fhe/sdk/dist/esm/query/index.d.ts` 和相关 SDK 类型入口。
