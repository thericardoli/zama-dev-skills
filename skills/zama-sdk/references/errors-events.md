# Errors、Events 与可观测性

本文件把 `Handle errors`、`Error types`、`Event decoders` 和源码中的 `errors/*`、`events/*` 合在一起。目标是让应用能把失败变成可恢复 UI，而不是只显示一段 raw error。

## 错误处理入口

所有 SDK typed errors 都继承 `ZamaError`，并带有稳定的 `.code` 字符串。

```ts
import {
  ZamaError,
  matchZamaError,
  SigningRejectedError,
  EncryptionFailedError,
} from "@zama-fhe/sdk";

try {
  await token.confidentialTransfer(to, amount);
} catch (error) {
  if (error instanceof SigningRejectedError) {
    return;
  }

  if (error instanceof EncryptionFailedError) {
    showError("加密失败，请重试");
    return;
  }

  if (error instanceof ZamaError) {
    showError(error.message);
    return;
  }

  throw error;
}
```

`matchZamaError` 适合 UI 层：

```ts
const message = matchZamaError(error, {
  SIGNING_REJECTED: () => "用户取消了钱包签名",
  INSUFFICIENT_CONFIDENTIAL_BALANCE: (e) => `私密余额不足：${e.message}`,
  INSUFFICIENT_ERC20_BALANCE: (e) => `公开 ERC20 余额不足：${e.message}`,
  BALANCE_CHECK_UNAVAILABLE: () => "需要先授权查看余额，或显式跳过余额检查",
  RELAYER_REQUEST_FAILED: (e) => `Relayer 请求失败：${e.message}`,
  _: (e) => (e instanceof Error ? e.message : "未知错误"),
});
```

## 常见错误码

| Error class | Code | 常见场景 | 建议处理 |
| --- | --- | --- | --- |
| `SigningRejectedError` | `SIGNING_REJECTED` | 用户拒绝 EIP-712 签名或交易 | 显示重试，不要当作系统错误 |
| `SigningFailedError` | `SIGNING_FAILED` | 钱包、硬件钱包或 RPC 签名失败 | 提示检查钱包连接 |
| `EncryptionFailedError` | `ENCRYPTION_FAILED` | FHE encryption worker/WASM 失败 | 检查 worker、CSP、输入类型 |
| `DecryptionFailedError` | `DECRYPTION_FAILED` | user/public decrypt 失败 | 检查 ACL、handle、pending unshield |
| `ApprovalFailedError` | `APPROVAL_FAILED` | public ERC20 approval 失败 | 检查 gas、allowance、token 行为 |
| `TransactionRevertedError` | `TRANSACTION_REVERTED` | 合约写入 revert | 解析 revert reason，刷新链上状态 |
| `InvalidKeypairError` | `INVALID_KEYPAIR` | relayer 拒绝 keypair | revoke session 后重新授权 |
| `KeypairExpiredError` | `KEYPAIR_EXPIRED` | `keypairTTL` 到期 | 重新 `allow()` |
| `NoCiphertextError` | `NO_CIPHERTEXT` | 账户从未有该 token encrypted balance | 显示空状态，不等同于 0 |
| `RelayerRequestFailedError` | `RELAYER_REQUEST_FAILED` | relayer/proxy 401、403、5xx、网络失败 | 检查 `relayerUrl`、API key、proxy |
| `ConfigurationError` | `CONFIGURATION` | import path、chain、worker、registry 配置错误 | 检查初始化配置 |
| `InsufficientConfidentialBalanceError` | `INSUFFICIENT_CONFIDENTIAL_BALANCE` | transfer/unshield 前余额不足 | 显示缺口，阻止提交 |
| `InsufficientERC20BalanceError` | `INSUFFICIENT_ERC20_BALANCE` | shield 前 public balance 不足 | 引导充值或减少金额 |
| `BalanceCheckUnavailableError` | `BALANCE_CHECK_UNAVAILABLE` | 没有 cached credentials，SDK 不想突然弹签名 | 提供授权按钮，或显式 `skipBalanceCheck` |
| `ERC20ReadFailedError` | `ERC20_READ_FAILED` | public ERC20 balance/allowance 读取失败 | 检查 RPC 和 token address |
| `DelegationSelfNotAllowedError` | `DELEGATION_SELF_NOT_ALLOWED` | delegate 等于当前用户 | 要求换 delegate |
| `DelegationDelegateEqualsContractError` | `DELEGATION_DELEGATE_EQUALS_CONTRACT` | delegate 等于 contract address | 要求换 delegate |
| `DelegationExpiryUnchangedError` | `DELEGATION_EXPIRY_UNCHANGED` | 新 expiry 与旧值相同 | 不发交易，提示已是当前设置 |
| `DelegationNotFoundError` | `DELEGATION_NOT_FOUND` | revoke 不存在的 delegation | 刷新状态 |
| `DelegationExpiredError` | `DELEGATION_EXPIRED` | delegation 已过期 | 重新授权 |
| `DelegationCooldownError` | `DELEGATION_COOLDOWN` | 同一区块重复 delegate/revoke | 等下一区块 |
| `DelegationContractIsSelfError` | `DELEGATION_CONTRACT_IS_SELF` | contract 等于 caller | 修正参数 |
| `DelegationExpirationTooSoonError` | `DELEGATION_EXPIRATION_TOO_SOON` | expiry 少于 1 小时 | 选择更远 expiry |
| `DelegationNotPropagatedError` | `DELEGATION_NOT_PROPAGATED` | delegation 已上链但 gateway 未同步 | 等待 1-2 分钟再重试 |
| `AclPausedError` | `ACL_PAUSED` | ACL contract paused | 停止相关操作，提示服务状态 |

## No ciphertext 与 zero balance

这是 UI 中最容易混淆的状态。

```ts
import { NoCiphertextError } from "@zama-fhe/sdk";

try {
  const balance = await token.balanceOf();
  renderBalance(balance); // 0n 是有效余额
} catch (error) {
  if (error instanceof NoCiphertextError) {
    renderEmptyState("还没有私密余额，请先 shield");
  }
}
```

`NoCiphertextError` 表示链上没有 encrypted balance handle；`0n` 表示 handle 存在且解密结果为 0。

## Relayer / Worker 状态

`RelayerWeb` 有初始化状态：

```ts
const relayer = new RelayerWeb({
  getChainId: () => signer.getChainId(),
  transports,
  onStatusChange: (status, error) => {
    console.debug("[zama-relayer]", status, error);
  },
});

console.log(relayer.status, relayer.initError);
```

常见状态：

- `idle`：还没有初始化。
- `initializing`：正在加载 worker/WASM。
- `ready`：可用。
- `error`：初始化失败，读 `initError`。

## SDK lifecycle events

`ZamaSDK` 支持 `onEvent`，适合调试和 telemetry。事件不会包含 private key 或明文 secret，但仍不要把完整对象无脑发到第三方日志。

```ts
const sdk = new ZamaSDK({
  relayer,
  signer,
  storage,
  onEvent: ({ type, ...event }) => {
    console.debug("[zama-sdk]", type, event);
  },
});
```

典型事件包括 encryption start/end/error、transaction submitted/error、delegation submitted、session revoked 等。精确事件枚举以 `node_modules/@zama-fhe/sdk/dist/esm/index.d.ts` 或 `packages/sdk/src/events/sdk-events.ts` 为准。

## Event decoders

SDK 提供 framework-agnostic raw log decoder。它们适用于 viem、ethers 或自定义 provider 返回的 log，只要有 `topics` 和 `data`。

```ts
import {
  TOKEN_TOPICS,
  ACL_TOPICS,
  decodeOnChainEvent,
  decodeOnChainEvents,
  findWrapped,
  findUnwrapRequested,
  decodeAclEvents,
} from "@zama-fhe/sdk";
```

抓取 token 事件：

```ts
const logs = await publicClient.getLogs({
  address: tokenAddress,
  topics: [TOKEN_TOPICS],
  fromBlock,
  toBlock: "latest",
});

const events = decodeOnChainEvents(logs);
```

事件对象使用 `eventName` 判别：

```ts
for (const event of events) {
  switch (event.eventName) {
    case "ConfidentialTransfer":
      console.log(event.from, event.to, event.encryptedAmountHandle);
      break;
    case "Wrapped":
      console.log(event.to, event.amountIn);
      break;
    case "UnwrapRequested":
      console.log(event.receiver, event.encryptedAmount);
      break;
    case "UnwrappedFinalized":
      console.log(event.receiver, event.cleartextAmount);
      break;
  }
}
```

便利查找：

```ts
const wrapped = findWrapped(receipt.logs);
const unwrap = findUnwrapRequested(receipt.logs);
```

ACL delegation events 要从 ACL contract 查：

```ts
const logs = await publicClient.getLogs({
  address: aclAddress,
  topics: [ACL_TOPICS],
  fromBlock,
  toBlock: "latest",
});

const aclEvents = decodeAclEvents(logs);
```

## Activity feed helpers

Activity feed 是 event decoders 上的一层：

```ts
import {
  parseActivityFeed,
  extractEncryptedHandles,
  applyDecryptedValues,
  sortByBlockNumber,
} from "@zama-fhe/sdk";

const items = parseActivityFeed(logs, userAddress);
const handles = extractEncryptedHandles(items);
const decrypted = await sdk.userDecrypt(
  handles.map((handle) => ({ handle, contractAddress: tokenAddress })),
);
const feed = sortByBlockNumber(applyDecryptedValues(items, decrypted));
```

`extractEncryptedHandles` 会跳过 zero handles 并去重。`applyDecryptedValues` 要求 decrypted value 是 `bigint`，因为 activity amount 是 token amount。

## 排障策略

优先按层排：

1. import path 是否正确。
2. chain id、transport preset、contract address 是否匹配。
3. relayer proxy 是否返回 401/403/5xx。
4. worker/WASM/CSP 是否阻止初始化。
5. wallet 是否支持 EIP-712 signing。
6. ACL 是否允许当前 user/delegate decrypt。
7. session/keypair TTL 是否过期。
8. handle 与 `contractAddress` 是否来自同一个合约。
9. token flow 是否把 public ERC20 allowance、confidential operator approval、delegated decrypt 混在一起。
