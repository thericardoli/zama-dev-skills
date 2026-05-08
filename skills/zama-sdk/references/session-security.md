# Session、凭证与安全边界

本文件补齐官方 `Session model` 和 `Security model` 的内容。它解释 SDK 为什么会弹钱包签名、哪些数据被持久化、TTL 怎么设置，以及浏览器/后端需要注意的安全边界。

## 先记住三件事

- SDK 保护的是 encrypted values 的读取能力，不会隐藏交易存在、调用类型、参与地址、token 地址、gas 或时间。
- 用户解密依赖两层材料：持久化的 FHE keypair，以及由钱包 EIP-712 签名解锁的 session signature。
- 浏览器里不能放 relayer API key；如果启用多线程 FHE，要配置 COOP/COEP；如果有 CSP，要允许 worker 和 WASM。

## 两层授权模型

SDK 的 user decrypt 不是每次都重新生成密钥。它拆成两层：

| 层 | 数据 | 默认位置 | 生命周期 |
| --- | --- | --- | --- |
| FHE keypair | public key + 加密后的 private key | `storage`，浏览器通常是 IndexedDB | 由 `keypairTTL` 控制 |
| Session signature | 钱包 EIP-712 签名 | `sessionStorage`，默认内存 | 由 `sessionTTL` 控制 |

流程：

1. 用户连接钱包。
2. SDK 生成 FHE keypair。
3. SDK 为指定 contract addresses 构造 EIP-712 typed data。
4. 用户签名。
5. SDK 用签名材料派生 AES-GCM key，加密 FHE private key 后写入 storage。
6. 当前 session 内再次 decrypt 时复用缓存签名，不再弹窗。

FHE private key 的明文只应在单次操作的 JS 内存中短暂存在；持久化存储里保存的是加密版本。

## TTL 规则

`ZamaSDK` 源码中的默认值：

| 选项 | 默认 | 说明 |
| --- | --- | --- |
| `keypairTTL` | `2592000` 秒，也就是 30 天 | FHE keypair 有效期；必须大于 0 |
| `sessionTTL` | `2592000` 秒，也就是 30 天 | session signature 有效期 |
| `registryTTL` | `86400` 秒，也就是 24 小时 | registry 查询缓存 |

重要边界：

- `keypairTTL: 0` 会抛错，因为 relayer 连接需要 keypair。
- `keypairTTL` 超过 365 天会被 capped 到 365 天并输出 warning。
- `sessionTTL: 0` 表示不缓存 session signature，每次需要 credentials 的操作都会要求钱包签名。
- Core `ZamaSDKConfig` 中 `sessionTTL: "infinite"` 表示 session signature 不主动过期；只在高信任环境里使用，并记住 keypair 仍受 `keypairTTL` 约束。React `ZamaProviderProps` 当前类型是 `number`，Provider 上使用字符串前先查本地类型。
- 如果数值型 `sessionTTL` 大于 `keypairTTL`，SDK 会把它 clamp 到 `keypairTTL`。

示例：

```ts
const sdk = new ZamaSDK({
  relayer,
  signer,
  storage,
  keypairTTL: 7 * 24 * 60 * 60,
  sessionTTL: 60 * 60,
});
```

## allow、isAllowed、revoke

最好的 UX 是显式授权，而不是页面一加载就触发钱包签名。

```ts
await sdk.allow([tokenA, tokenB, vaultAddress]);
const ok = await sdk.credentials.isAllowed([tokenA]);
const values = await sdk.userDecrypt([{ handle, contractAddress: tokenA }]);
```

React：

```tsx
const allow = useAllow();
const { data: allowed } = useIsAllowed({
  contractAddresses: [tokenAddress],
});

const balance = useConfidentialBalance(
  { tokenAddress },
  { enabled: !!allowed },
);

if (!allowed) {
  return <button onClick={() => allow.mutate([tokenAddress])}>授权查看余额</button>;
}
```

一次 `allow()` 可以覆盖多个 contract address。尽量把同一页面或同一产品流程会读取的 contracts 一次性传入，避免之后每新增一个地址都重新弹签名。

撤销：

```ts
await sdk.revokeSession();
await token.revoke(token.address);
sdk.dispose();
sdk.terminate();
```

- `revokeSession()` 清掉 session signature 和相关 decrypt cache。
- `dispose()` 取消 signer lifecycle subscription，不关闭 relayer worker。
- `terminate()` 会调用 `dispose()`，并关闭 `RelayerWeb` worker 或 `RelayerNode` pool。

## 钱包生命周期

`WagmiSigner` 已实现 `subscribe()`，`ZamaProvider` / `ZamaSDK` 会组合它的 lifecycle 事件并刷新相关 cache。

自定义 signer、部分 viem/ethers 封装需要自己处理：

```ts
wallet.on("disconnect", () => sdk.revokeSession());
wallet.on("accountsChanged", () => sdk.revokeSession());
```

原则：

- disconnect / lock：清掉当前 session。
- account change：清掉旧账号 session，避免 UI 显示错账号的授权状态。
- chain change：credentials 按 address + chain 隔离；切链后要刷新 query 和 contract addresses，不要复用 handle。

## 浏览器安全

### API key

浏览器永远不要包含：

```ts
auth: { __type: "ApiKeyHeader", value: "..." }
```

前端只指向 proxy：

```ts
relayerUrl: "/api/relayer/11155111"
```

服务端 proxy 注入 `x-api-key`，并按项目需要加入登录态、rate limit 和 CSRF protection。

### WASM、worker 和 CSP

`RelayerWeb` 会在 Web Worker 中加载 pinned CDN WASM bundle，并默认做 SHA-384 integrity check。不要在生产关闭：

```ts
const relayer = new RelayerWeb({
  getChainId: () => signer.getChainId(),
  transports,
  security: { integrityCheck: true },
});
```

如果应用设置了严格 CSP，通常需要允许：

```txt
worker-src blob:;
script-src 'self' 'wasm-unsafe-eval';
connect-src 'self' https://cdn.zama.org https://your-relayer-proxy.example;
```

### COOP/COEP

只有启用多线程 `threads` 或需要 `SharedArrayBuffer` 性能路径时，才需要跨源隔离 headers：

```txt
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

没有这些 headers 时，SDK 会尝试 fallback 到单线程。结果是性能下降，不应直接当作功能必然不可用。

## 数据可见性

FHE 保护 value，不保护所有 metadata。

公开可见：

- 交易发生了
- 调用了哪个合约、哪个函数
- 参与地址
- token 地址
- gas、时间和区块位置
- shield/unshield 这类 public/confidential 边界流程中的部分 clear amount 或 public ERC20 transfer 信息

应视为 confidential 的：

- confidential transfer amount
- confidential balance handle 对应的明文 balance
- 自定义合约中未公开授权的 encrypted state

如果产品承诺“完全隐藏交易关系”或“shield 金额也不可见”，需要额外协议设计；SDK 本身不提供 transaction graph privacy。

## 后端安全

Node 服务端可以直接使用 relayer API key：

```ts
auth: { __type: "ApiKeyHeader", value: process.env.RELAYER_API_KEY! }
```

但要注意：

- private key、mnemonic、API key 必须来自环境变量或 secret manager。
- 多用户服务不要共享 `memoryStorage`；用 `asyncLocalStorage` 或请求级 SDK。
- 不要把 signed typed data、private key、session signature、raw credentials 打进日志。
- 长生命周期进程退出时调用 `sdk.terminate()`。

## 安全检查清单

- 前端 bundle 中没有 relayer API key。
- `ZamaProvider` 只在 client component 中使用。
- `useUserDecrypt` / `useConfidentialBalance` 有显式授权 gate。
- 所有 `handle` 都配对正确的 `contractAddress`。
- `keypairTTL`、`sessionTTL` 是产品有意识的选择。
- 自定义 signer 实现了账号/断连 lifecycle，或手动 revoke。
- CSP 覆盖 worker、WASM 和 CDN。
- public decrypt 只用于合约明确允许公开的值。
- shield/unshield 边界金额在 UX 和隐私说明里没有被误描述。
