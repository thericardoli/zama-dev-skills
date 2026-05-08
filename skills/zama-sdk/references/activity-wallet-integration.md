# Activity Feed、钱包与交易所集成

本文件覆盖官方 `Activity feeds`、`Wallet & exchange integration` 和 `Operator approvals` 中与产品集成最相关的部分。它适合钱包、portfolio dashboard、交易所、custodial 后端和需要展示 token 历史记录的 dApp。

## 钱包/交易所需要支持什么

ERC7984 confidential token 不是普通 ERC20 的简单 UI 皮肤。集成方通常需要支持：

- 发现 public ERC20 与 confidential wrapper 的映射。
- 展示 metadata、public ERC20 balance、confidential balance。
- 通过 user decrypt 显示用户自己的 confidential balance。
- 构建 confidential transfer，并在客户端加密 amount。
- 支持 operator approval 和 `confidentialTransferFrom`。
- 支持 shield/unshield，以及中断后的 unshield resume。
- 解析事件生成 activity feed。

不需要自己运行 FHE 基础设施。应用通过 SDK 调 relayer、chain RPC 和 wallet 即可。

## 关键隐私边界

Confidential transfer 的 amount 是 encrypted input；链上观察者看不到转账金额。

但是 shield/unshield 是 public ERC20 与 confidential token 的边界流程：

- shield 会涉及 public ERC20 approval / transfer，wrapper 事件里也有 clear amount。
- unshield 最终会把明文 public ERC20 数量释放出来，finalize 事件里有 clear amount。

因此钱包和交易所文案不要承诺“所有金额始终不可见”。更准确的表达是：进入 confidential token 后，balance 和 confidential transfer amount 是加密的；进出 public ERC20 边界时，边界金额按 public token 规则可见。

## Registry Discovery

使用 SDK registry，不要硬编码当前注册 token 地址。

```ts
const result = await sdk.registry.getConfidentialToken(publicTokenAddress);

if (result?.isValid) {
  const token = sdk.createToken(result.confidentialTokenAddress);
}
```

反查 confidential token 的 underlying public ERC20：

```ts
const result = await sdk.registry.getUnderlyingToken(confidentialTokenAddress);

if (result?.isValid) {
  console.log(result.tokenAddress);
}
```

分页列出 pairs：

```ts
const page = await sdk.registry.listPairs({
  page: 1,
  pageSize: 20,
  metadata: true,
});

for (const pair of page.items) {
  console.log(pair.underlying.symbol, pair.confidential.symbol);
}
```

React：

```tsx
const { data } = useConfidentialTokenAddress({
  tokenAddress: publicTokenAddress,
});

const confidentialTokenAddress = data?.[0] ? data[1] : undefined;

const { data: isValid } = useIsConfidentialTokenValid({
  confidentialTokenAddress,
});

const { data: reverse } = useTokenAddress({
  confidentialTokenAddress,
});

const { data: pairs } = useListPairs({
  page: 1,
  pageSize: 20,
  metadata: true,
});
```

Core `sdk.registry.getConfidentialToken(...)` / `getUnderlyingToken(...)` 返回 structured object，包含 `isValid`。React 的低层 registry hooks 返回 tuple；先检查 tuple 第一个元素是否为 `true`，再用 `useIsConfidentialTokenValid` 验证当前 confidential token 是否仍有效。registry 中查到非零地址不代表仍可用。

## 余额展示

第一次 user decrypt 会触发 EIP-712 签名。钱包或交易所 UI 应提供明确动作，例如“查看私密余额”。

```tsx
const { mutate: allow, isPending: isAllowing } = useAllow();
const { data: allowed } = useIsAllowed({
  contractAddresses: [tokenAddress],
});

const balance = useConfidentialBalance(
  { tokenAddress },
  { enabled: !!allowed },
);

if (!allowed) {
  return (
    <button onClick={() => allow([tokenAddress])} disabled={isAllowing}>
      {isAllowing ? "签名中..." : "查看私密余额"}
    </button>
  );
}
```

区分三个状态：

| 状态 | 含义 | UI |
| --- | --- | --- |
| no ciphertext | 账户从未 shield 过该 token | 显示空状态，引导 shield |
| zero balance | 曾有 encrypted balance，但现在是 `0n` | 显示 0 |
| decrypt unavailable | 用户未授权或 relayer/auth 出错 | 显示授权或重试 |

## Confidential Transfer

高层 API：

```ts
const token = sdk.createToken(confidentialTokenAddress);
const { txHash, receipt } = await token.confidentialTransfer(recipient, 500n);
```

React：

```tsx
const transfer = useConfidentialTransfer({
  tokenAddress,
  optimistic: true,
});

await transfer.mutateAsync({
  to: recipient,
  amount: 500n,
});
```

默认情况下 SDK 会在 transfer 前尝试验证 confidential balance。如果没有 cached credentials，会抛 `BalanceCheckUnavailableError`，避免突然弹签名。只有明确接受链上 revert 风险时才传 `skipBalanceCheck: true`。

## Operator Approval

Operator approval 类似 ERC20 approve/transferFrom，但授权的是 encrypted token operator，不是 underlying public ERC20 allowance。

```ts
await token.approve(spender);

const expiry = Math.floor(Date.now() / 1000) + 24 * 60 * 60;
await token.approve(spender, expiry);

const approved = await token.isApproved(spender, owner);
```

Operator 转账：

```ts
await token.confidentialTransferFrom(owner, recipient, amount);
```

React：

```tsx
const approve = useConfidentialApprove({ tokenAddress });
const status = useConfidentialIsApproved({ tokenAddress, spender });
const transferFrom = useConfidentialTransferFrom({ tokenAddress });

await approve.mutateAsync({ spender, until: expiry });
await transferFrom.mutateAsync({ from: owner, to: recipient, amount });
```

UX 注意：

- approval 应有明确 expiry，不要默认做永久授权。
- 显示 operator 可以代用户移动 confidential balance 的风险。
- revoke 或修改 expiry 要容易找到。
- public ERC20 allowance、confidential operator approval、delegated decryption 是三套不同机制。

## Delegated Decryption

Delegated decryption 允许 delegate 读取 delegator 在某个 confidential contract 上被授权的 encrypted values。它适合 portfolio service、custodial read、合规报表或企业后台。

```ts
await token.delegateDecryption({
  delegateAddress,
  expirationDate: new Date(Date.now() + 24 * 60 * 60 * 1000),
});

await token.revokeDelegation({ delegateAddress });
```

批量：

```ts
const results = await Token.batchDelegateDecryption({
  tokens,
  delegateAddress,
  expirationDate,
});
```

读取：

```ts
const value = await readonlyToken.decryptBalanceAs({
  delegatorAddress,
});
```

注意：

- delegate 不能等于 delegator 自己。
- delegate 不能等于 token contract address。
- expiration 至少应在 1 小时以后，否则 SDK 会抛 `DelegationExpirationTooSoonError`。
- delegation 上链后需要等待 gateway 同步，太快读取可能遇到 `DelegationNotPropagatedError`。
- delegation 只授权读取，不是 operator transfer approval。

## Activity Feed Pipeline

SDK 提供纯函数把 raw logs 转成可渲染 feed：

```ts
import {
  TOKEN_TOPICS,
  parseActivityFeed,
  extractEncryptedHandles,
  applyDecryptedValues,
  sortByBlockNumber,
} from "@zama-fhe/sdk";

const logs = await publicClient.getLogs({
  address: tokenAddress,
  topics: [TOKEN_TOPICS],
  fromBlock,
  toBlock: "latest",
});

const items = parseActivityFeed(logs, userAddress);
const handles = extractEncryptedHandles(items);

const decrypted = await sdk.userDecrypt(
  handles.map((handle) => ({ handle, contractAddress: tokenAddress })),
);

const feed = sortByBlockNumber(applyDecryptedValues(items, decrypted));
```

`ActivityItem` 的核心字段：

| 字段 | 含义 |
| --- | --- |
| `type` | `"transfer"`、`"shield"`、`"unshield_requested"`、`"unshield_started"`、`"unshield_finalized"` |
| `direction` | `"incoming"`、`"outgoing"`、`"self"` |
| `amount` | clear amount 或 encrypted handle，解密后填充 `decryptedValue` |
| `from` / `to` | 事件参与地址 |
| `metadata` | tx hash、block number、log index |
| `rawEvent` | 原始 decoded event |

React hook：

```tsx
const { data: feed, isLoading } = useActivityFeed({
  tokenAddress,
  userAddress,
  logs,
  decrypt: true,
});
```

源码中 `decrypt` 默认是 `true`。设置 `decrypt: false` 时只做事件分类，不解密 encrypted amount。适合公开 activity 列表、未授权状态或性能预览。

## Event Decoders

如果只需要较低层的事件解析：

```ts
import {
  decodeOnChainEvents,
  decodeConfidentialTransfer,
  decodeWrapped,
  decodeUnwrapRequested,
  findWrapped,
  findUnwrapRequested,
  ACL_TOPICS,
  decodeAclEvents,
} from "@zama-fhe/sdk";
```

事件对象使用 `eventName` 判别：

```ts
const events = decodeOnChainEvents(receipt.logs);

for (const event of events) {
  if (event.eventName === "ConfidentialTransfer") {
    console.log(event.from, event.to, event.encryptedAmountHandle);
  }
}
```

ACL delegation events 不在 `TOKEN_TOPICS` 中。它们由 ACL contract 发出，需要单独用 `ACL_TOPICS` 查询。

## 钱包/交易所 UX 检查清单

- Registry 查询结果检查 `isValid`。
- 不硬编码官方当前注册 token 地址；允许 registry refresh。
- 展示 public ERC20 balance 和 confidential balance 时明确区分。
- 首次 decrypt 由用户点击触发。
- `NoCiphertextError` 与 `0n` 分开显示。
- shield/unshield 明确显示 public 边界金额可见。
- transfer 前显示 operator/approval/decryption 的真实状态。
- unshield 存在 pending 状态时允许 resume。
- activity feed 支持分页或 indexer，不要一次扫全链。
- delegation 状态要显示 expiry、delegate 和 revoke action。
