# Node、后端和本地开发

本文件适用于脚本、后端服务、relayer proxy routes、server jobs 和本地 cleartext 开发。

Node 路径使用 `RelayerNode`，它来自 `@zama-fhe/sdk/node` 子路径，并依赖 Node.js `>=22`。它使用 native worker threads，不使用 browser Web Worker。

## Node SDK 工厂

```ts
import { ZamaSDK, SepoliaConfig, memoryStorage } from "@zama-fhe/sdk";
import { RelayerNode } from "@zama-fhe/sdk/node";
import { ViemSigner } from "@zama-fhe/sdk/viem";

export function createZamaSdk({ walletClient, publicClient }: Clients) {
  const signer = new ViemSigner({ walletClient, publicClient });

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

  return new ZamaSDK({
    relayer,
    signer,
    storage: memoryStorage,
  });
}
```

这类写法用于可信脚本和服务。私有值放在环境变量或 secret manager 中。

## 请求级 Storage

多用户服务器不要在不相关用户之间共享同一个 `memoryStorage`：

```ts
import { ZamaSDK } from "@zama-fhe/sdk";
import { asyncLocalStorage } from "@zama-fhe/sdk/node";

export async function withZamaRequest<T>(fn: (sdk: ZamaSDK) => Promise<T>) {
  return asyncLocalStorage.run(async () => {
    const sdk = new ZamaSDK({
      relayer,
      signer,
      storage: asyncLocalStorage,
    });

    return fn(sdk);
  });
}
```

当 decrypt credentials 或 cache 依赖当前用户时，使用 request-scoped storage。

Express/Hono/Next route 中要确保 SDK 操作发生在 `asyncLocalStorage.run()` 回调内部；在回调外创建的 promise 不会自动继承这次 request scope。

## 后端 Proxy

Browser 应用在需要私有 relayer credentials 时，应调用同源 route：

```ts
export async function POST(request: Request) {
  const upstream = await fetch(process.env.ZAMA_RELAYER_URL!, {
    method: "POST",
    headers: {
      "content-type": request.headers.get("content-type") ?? "application/json",
      "x-api-key": process.env.RELAYER_API_KEY!,
    },
    body: await request.text(),
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: upstream.headers,
  });
}
```

根据具体框架调整 path forwarding、CORS、streaming 和 headers。架构原则是：browser 只调用 `/api/relayer/<chain>`，server 注入私有 credentials。

## 公开解密任务

服务端 job 常见职责是监听合约、请求 public decrypt，然后提交 finalize 交易：

```ts
const result = await sdk.publicDecrypt([handle]);

await sdk.signer.writeContract({
  address: contractAddress,
  abi,
  functionName: "finalizeReveal",
  args: [result.abiEncodedClearValues, result.decryptionProof],
});
```

提交 callback 前检查：

- 合约确实为该 handle 请求了 public decrypt
- callback ABI 与 proof encoding 匹配
- 已处理 replay 和 already-finalized 状态
- 如果应用对 reorg 敏感，等待足够 confirmations

## 本地 Cleartext Runtime

```ts
import { ZamaSDK, memoryStorage } from "@zama-fhe/sdk";
import {
  RelayerCleartext,
  hardhatCleartextConfig,
  hoodiCleartextConfig,
} from "@zama-fhe/sdk/cleartext";

const relayer = new RelayerCleartext(hardhatCleartextConfig);
const sdk = new ZamaSDK({ relayer, signer, storage: memoryStorage });
```

Cleartext 模式适合：

- 本地合约 demo
- deterministic integration tests
- 不想等待远端 proof 的前端开发
- 连接真实 FHE 网络前调试 app 编排

不要把 cleartext 模式用于 production、Sepolia 或 Mainnet 路径。

SDK 源码明确阻止 cleartext mode 在 Ethereum Mainnet (`1`) 和 Sepolia (`11155111`) 上运行。Hoodi cleartext preset 是独立的开发/测试配置：

```ts
import { RelayerCleartext, hoodiCleartextConfig } from "@zama-fhe/sdk/cleartext";

const relayer = new RelayerCleartext(hoodiCleartextConfig);
```

自定义 cleartext chain 需要提供 `CleartextConfig`，其中 `executorAddress` 必须对应本地部署的 cleartext executor。

## Worker 和生命周期管理

Node relayer runtime 可能持有 worker threads 或 pools。长生命周期进程需要干净关闭：

```ts
process.on("SIGTERM", () => {
  sdk.terminate();
  process.exit(0);
});
```

短脚本：

```ts
try {
  await main();
} finally {
  sdk.terminate();
}
```

## CLI 脚本模式

```ts
async function main() {
  const sdk = createZamaSdk();
  const userAddress = await sdk.signer.getAddress();

  const encrypted = await sdk.relayer.encrypt({
    values: [{ type: "euint64", value: 10n }],
    contractAddress,
    userAddress,
  });

  // 写合约、等待 receipt，然后按需 decrypt
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
```

脚本要尽量幂等。写交易前打印 tx hashes、chain id、contract address 和 signer address。

## 服务端安全检查清单

- private key 或 mnemonic 不进 repo
- API key 不暴露给 browser bundle
- 涉及用户 decrypt 时使用 per-request cache isolation
- worker shutdown 时调用 `terminate()`
- 写交易前显式检查 chain id 和 contract address
- public decrypt callback 有 replay protection
- logs 不打印 private keys、signed typed data 或 decrypt secrets
