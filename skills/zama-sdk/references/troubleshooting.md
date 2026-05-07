# 排障

本文件列出常见失败模式、可能原因和最快检查顺序。

## 导入或导出错误

先检查 import path：

- `RelayerNode` 来自 `@zama-fhe/sdk/node`
- `RelayerCleartext` 来自 `@zama-fhe/sdk/cleartext`
- `ViemSigner` 来自 `@zama-fhe/sdk/viem`
- `EthersSigner` 来自 `@zama-fhe/sdk/ethers`
- `WagmiSigner` 来自 `@zama-fhe/react-sdk/wagmi`

然后检查：

```bash
cat package.json
rg "@zama-fhe/(sdk|react-sdk)|RelayerWeb|RelayerNode|RelayerCleartext|ZamaProvider|WagmiSigner|ViemSigner|EthersSigner"
```

如果 pnpm 安装时报 `No matching version found for @zama-fhe/react-sdk@...`，说明示例或模型记忆里的版本已经过期。先查询真实版本，再同步两个 SDK 包：

```bash
pnpm view @zama-fhe/sdk versions --json
pnpm view @zama-fhe/react-sdk versions --json
```

如果生产构建时报 `"watchConnection" is not exported by "wagmi/actions"` 或类似 wagmi action export mismatch，问题在 `@zama-fhe/react-sdk/wagmi` adapter 与当前 wagmi 版本不匹配。不要改 `node_modules`；使用 `configuration.md` 里的 custom `GenericSigner` fallback，或固定到已验证的 SDK/wagmi/viem 版本组合。

## `window is not defined` 或 SSR Crash

可能原因：

- server component import 了 React SDK hook
- 在 server-side module scope 创建了 `RelayerWeb`
- provider 文件缺少 `"use client"`
- client/server 共享模块实例化了 browser SDK 代码

修复：

- 把 provider 和 SDK browser runtime 移到 client component
- server-only API route code 与 browser code 分离
- 必要时动态 import client-only components

## Worker、WASM 或 SharedArrayBuffer 问题

症状：

- encryption 卡在 initialization
- browser console 提到 worker 或 WASM loading
- browser console 提到 COOP/COEP 或 SharedArrayBuffer
- `relayer.status === "error"`

检查：

1. 查看 `relayer.initError`。
2. 如可用，使用 `onStatusChange` 加 status logging。
3. 配置 headers：

```txt
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

4. 如果配置了 `threads`，先把 thread count 设为 1 或移除 `threads`，确认单线程 fallback 是否可用。
5. 如果应用有 CSP，确认允许 `worker-src blob:`、`script-src 'wasm-unsafe-eval'` 和 `connect-src https://cdn.zama.org`。
6. 确认 bundler 没有把 SDK runtime 放进 server code。

## 浏览器 Credential 暴露

危险信号：

```ts
auth: { __type: "ApiKeyHeader", value: "..." }
```

出现在 browser code 中。

修复 browser config，改用 proxy URL：

```ts
relayerUrl: "/api/relayer/11155111"
```

私有 credentials 只放在 server-side route handlers、workers、jobs 或 secret managers 中。

## 加密合约调用 Revert

检查：

- 加密时使用的 `contractAddress` 是否是调用 `FHE.fromExternal` 的合约
- `userAddress` 是否是 connected account
- chain id 是否匹配 deployed contract 和 SDK transport
- ABI function name 和 argument order 是否正确
- handles 和 input proof 是否来自同一次 encrypt 调用
- `Uint8Array` 是否只转 hex 一次
- Solidity 函数是否接收 encrypted external type 加 proof
- 合约保存新 handles 后是否正确传播 ACL

## 用户解密失败

按顺序检查：

1. handle 是否是 zero handle；zero handle 直接显示 0。
2. handle 是否属于传入的 `contractAddress`。
3. 合约是否允许当前 user 或 delegate。
4. app 是否对所有需要的 contracts 调用了 `sdk.allow` 或 `useAllow`。
5. session 是否过期。
6. account 或 chain 是否变化。
7. relayer proxy 是否返回 401、403 或 5xx。
8. storage 是否在用户之间错误共享。

## 意外的钱包签名弹窗

常见原因：cached authorization 未确认前 decrypt query 就启动了。

修复：

```tsx
const { data: allowed } = useIsAllowed({
  contractAddresses: [contractAddress],
});

const decrypt = useUserDecrypt(
  { handles: [{ handle, contractAddress }] },
  { enabled: !!allowed },
);
```

优先提供显式的 "授权" 动作，调用 `useAllow`。

## 公开解密失败

public decrypt 只适用于合约逻辑明确公开的 handles。

检查：

- 合约是否已 request 或标记该值可 public decrypt
- handle 是否来自正确 contract 和 chain
- app 是否等待了所需 off-chain proof flow
- finalize ABI 是否期望当前提交的 clear value encoding
- callback 是否有 replay protection 和 requested/finalized guards

## Token 余额检查错误

token operation 的 balance check 可能需要 decrypt credentials。

如果 balance check unavailable：

- 调用 `token.allow()`、`sdk.allow([tokenAddress])` 或 `useAllow`
- 只有显式接受链上 revert 风险时才使用 `skipBalanceCheck`
- account、chain 或 token 变化后刷新 balance handles

如果 balance 不足：

- 检查 token decimals
- 检查 connected account
- 区分 public ERC20 balance 和 confidential balance
- 检查 wrapper 和 underlying token addresses

如果抛 `NoCiphertextError`：

- 这表示账户没有 encrypted balance handle，不等于 `0n`
- UI 应显示空状态或引导 shield
- 不要把它归类为 relayer failure

## Registry 或 Wrapper 找不到

检查：

- 当前 chain 是否配置了 registry
- 本地 chain 是否使用 `registryAddresses`
- token 是否支持预期 ERC7984 interfaces
- wrapper 是否有预期的 underlying public ERC20
- signer 中的 chain id 是否与 registry override chain id 匹配

## 本地 Cleartext 不匹配

Cleartext 模式只适用于兼容的本地 cleartext deployment。

失败信号：

- 在 Sepolia 或 Mainnet 使用 cleartext runtime
- 本地合约部署的 FHE mode 与 cleartext runtime 不匹配
- app 期待 public decrypt proof behavior，但 cleartext setup 不支持
- contract addresses 从另一次 local node session 复制过来

快速检查：

```bash
cast client --rpc-url http://127.0.0.1:8545
cast chain-id --rpc-url http://127.0.0.1:8545
```

如果 forge-fhevm `deploy-local.sh` 报 `could not detect a supported local RPC backend`，显式传：

```bash
LOCAL_STATE_RPC_NAMESPACE=anvil ./dependencies/forge-fhevm-<version>/deploy-local.sh --anvil-port 8545
```

## 安全检查清单

- API keys 只在服务端
- mnemonic/private key 不提交
- frontend config 只包含公开值
- user decrypt authorization 只覆盖必要 contracts
- session TTL 是有意设置的
- account 或 chain 变化时清理 decrypt cache
- 合约 ACL 与 UI decrypt 假设一致
- public decrypt 只用于公开数据
- logs 不包含 secrets、private keys 或敏感 signatures
