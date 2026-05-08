# ERC7984 Token 工作流

本文件适用于 ERC7984 confidential token UI、wrapped ERC20 flow、registry discovery、shield token、private transfer、unshield token 和 balance check。它按官方 Guides 的划分组织：shield、私密转账、unshield、余额检查和错误处理。

## 何时使用 Token API

当目标合约是 ERC7984 confidential token 或 wrapper 时，使用 `Token`、`ReadonlyToken` 和 token hooks。

不要把 token API 用于任意 FHE 合约，例如 auction、vault、private counter 或 voting contract。这些场景读 `custom-contracts.md`。

## 创建 Token 对象

`sdk.createToken(address, wrapper?)` 的第一个参数是 **ERC7984 confidential token contract address**，不是 underlying public ERC20 address。

```ts
const token = sdk.createToken(confidentialTokenAddress);
```

返回值是一个 `Token` 实例。`Token` 继承 `ReadonlyToken`，因此既有 metadata、balance、allow/decrypt 这类只读能力，也有 shield、confidential transfer、operator approval、unshield、delegation 这类写操作。

地址角色：

| 地址 | 含义 | 传给哪里 |
| --- | --- | --- |
| `publicTokenAddress` | underlying public ERC20，例如普通 USDC/ERC20 | 不传给 `createToken`；用于 registry lookup、展示 public balance、或底层 ERC20 读写 |
| `confidentialTokenAddress` | ERC7984 confidential token contract | `sdk.createToken(confidentialTokenAddress)` 的第一个参数 |
| `wrapperAddress` | wrap/unwrap public ERC20 的 wrapper contract；有些部署中它可能和 confidential token address 相同 | `sdk.createToken(confidentialTokenAddress, wrapperAddress)` 的第二个参数 |

显式传 wrapper：

```ts
const token = sdk.createToken(confidentialTokenAddress, wrapperAddress);
```

如果没有传 `wrapperAddress`，SDK 会默认把 wrapper 视为 `confidentialTokenAddress`。这只适用于 confidential token 合约本身就是 wrapper 的部署；wrapped ERC20 项目通常应显式传入 registry 发现到的 wrapper address。

只读：

```ts
const readonlyToken = sdk.createReadonlyToken(confidentialTokenAddress);
```

## Shield 流程

Public ERC20 转 confidential token：

```ts
await token.shield(1000n);
```

Options：

| Option | 含义 |
| --- | --- |
| `approvalStrategy` | `"exact"`、`"max"` 或 `"skip"` |
| `to` | confidential token recipient |
| `onApprovalSubmitted` | public approval tx hash callback |
| `onShieldSubmitted` | shield tx hash callback |

SDK 会处理 public ERC20 balance check、approval 和 wrapper `wrap` transaction。它会先检查 public ERC20 balance。public balance 不足会抛 `InsufficientERC20BalanceError`。

注意：shield 是 public ERC20 进入 confidential token 的边界操作。public ERC20 transfer/approval 和 wrapper event 中的边界金额通常是可见的；进入 confidential token 之后的 balance 和 subsequent confidential transfer amount 才按 FHE 流程隐藏。

## 检查余额

解密 balance：

```ts
await token.allow();
const balance = await token.balanceOf();
```

读取 encrypted handle：

```ts
const handle = await token.confidentialBalanceOf(owner);
```

当 UI 只需要 handle，或需要自定义 decrypt 编排时，使用 `confidentialBalanceOf`。

React：

```tsx
const { data: balance, isLoading } = useConfidentialBalance({ tokenAddress });
```

当前 React hook 读取的是当前 signer 的 balance。如果要展示任意 owner，使用 core API：

```ts
const rt = sdk.createReadonlyToken(confidentialTokenAddress);
const balance = await rt.balanceOf(owner);
const handle = await rt.confidentialBalanceOf(owner);
```

第一次 decrypt 可能需要钱包签名。之后 cached credentials 和 decrypt cache 会让后续读取免于重复弹窗，直到 TTL、revoke、account change 或 chain change。

## 私密转账

```ts
await token.confidentialTransfer(recipient, 500n);
```

Options：

| Option | 含义 |
| --- | --- |
| `skipBalanceCheck` | 跳过本地 confidential balance decrypt check |
| `onEncryptComplete` | FHE encryption 完成后调用 |
| `onTransferSubmitted` | transfer tx callback |

SDK 会在客户端加密 amount，然后写入 transfer。默认行为会在 transfer 前解密 confidential balance 做检查。如果钱包无法签 decrypt credentials，smart wallet flow 可能需要 `skipBalanceCheck`，但要接受链上 revert 风险。

React：

```tsx
const transfer = useConfidentialTransfer({ tokenAddress });
await transfer.mutateAsync({ to: recipient, amount: 500n });
```

## Operator 转账

```ts
await token.confidentialTransferFrom(from, to, 500n);
```

需要 confidential operator approval。

## Confidential 授权

```ts
await token.approve(spender);
await token.approve(spender, expiryTimestamp);
const ok = await token.isApproved(spender);
```

这是 confidential token operator approval，不是 public ERC20 allowance，也不是 delegated decryption。默认 `approve(spender)` 使用约 1 小时窗口；生产 UI 应让用户看见 spender、expiry 和 revoke/更新入口。

React：

```tsx
const approve = useConfidentialApprove({ tokenAddress });
const approved = useConfidentialIsApproved({ tokenAddress, spender });
const transferFrom = useConfidentialTransferFrom({ tokenAddress });

await approve.mutateAsync({ spender, until: expiryTimestamp });
await transferFrom.mutateAsync({ from, to, amount });
```

## Unshield 流程

Confidential token 转 public ERC20：

```ts
await token.unshield(500n);
```

它会编排：

1. phase 1 unwrap/burn request
2. public decrypt proof retrieval
3. phase 2 finalize

Options：

| Option | 含义 |
| --- | --- |
| `skipBalanceCheck` | 跳过 confidential balance check |
| `onUnwrapSubmitted` | phase 1 tx callback |
| `onFinalizing` | proof/finalize phase starts |
| `onFinalizeSubmitted` | phase 2 tx callback |

恢复中断流程：

```ts
await token.resumeUnshield(unwrapTxHash);
```

Storage helpers：

```ts
import { loadPendingUnshield, clearPendingUnshield } from "@zama-fhe/sdk";

const pending = await loadPendingUnshield(storage, wrapperAddress);
if (pending) {
  await token.resumeUnshield(pending);
  await clearPendingUnshield(storage, wrapperAddress);
}
```

React：

```tsx
const unshield = useUnshield({ tokenAddress, wrapperAddress });
await unshield.mutateAsync({ amount: 500n });
```

pending unshield UX 很重要，因为 unshield 跨多个 phase。持久化足够状态，允许用户恢复 finalize。

全部 unshield：

```ts
await token.unshieldAll();
```

React：

```tsx
const unshieldAll = useUnshieldAll({ tokenAddress, wrapperAddress });
await unshieldAll.mutateAsync();
```

如果产品需要完全手动控制两阶段流程，使用低层 `unwrap` / `finalizeUnwrap`：

```ts
const unwrap = await token.unwrap(500n);
const event = findUnwrapRequested(unwrap.receipt.logs);
if (event) {
  await token.finalizeUnwrap(event.encryptedAmount);
}
```

## Underlying ERC20 授权

```ts
await token.approveUnderlying();
await token.approveUnderlying(1000n);
```

在 `shield(..., { approvalStrategy: "skip" })` 前常用，或用于产品希望把 approval 单独做成一步的场景。

React：

```tsx
const { data: allowance } = useUnderlyingAllowance({
  tokenAddress,
  wrapperAddress,
});

const approveUnderlying = useApproveUnderlying({
  tokenAddress,
  wrapperAddress,
});

await approveUnderlying.mutateAsync({}); // max approval
await approveUnderlying.mutateAsync({ amount: 1000n }); // exact approval
```

## ReadonlyToken 只读接口

```ts
const rt = sdk.createReadonlyToken(tokenAddress);
```

常用 methods：

| 方法 | 含义 |
| --- | --- |
| `balanceOf(owner?)` | 解密 confidential balance |
| `confidentialBalanceOf(owner?)` | encrypted balance handle |
| `name()` | token name |
| `symbol()` | token symbol |
| `decimals()` | decimals |
| `isConfidential()` | ERC7984 support |
| `isWrapper()` | wrapper detection |
| `underlyingToken()` | underlying public ERC20 |
| `allowance(wrapper, owner?)` | public ERC20 allowance |
| `allow()` / `revoke()` / `isAllowed()` | decrypt session management |

zero handle 工具从 SDK 导入：

```ts
import { isZeroHandle, ZERO_HANDLE } from "@zama-fhe/sdk";
```

批量 balances：

```ts
const tokens = addresses.map((address) => sdk.createReadonlyToken(address));
await ReadonlyToken.allow(...tokens);
const { results, errors } = await ReadonlyToken.batchBalancesOf(tokens, owner);
```

单个 token 失败不会 reject 整个批处理。

## Registry 注册表

```ts
const pairs = await sdk.registry.listPairs({ page: 1 });
const confidential = await sdk.registry.getConfidentialToken(publicToken);
const publicToken = await sdk.registry.getUnderlyingToken(confidentialToken);
```

自定义 registry：

```ts
const registry = sdk.createWrappersRegistry({
  [31337]: "0xRegistry",
});
```

## Delegated Decryption

Delegated decryption 是“授权读取”，不是“授权转账”。

```ts
await token.delegateDecryption({
  delegateAddress,
  expirationDate: new Date(Date.now() + 24 * 60 * 60 * 1000),
});

await token.revokeDelegation({ delegateAddress });
```

读取 delegation 状态或作为 delegate 解密 balance：

```ts
const delegated = await token.isDelegated({
  delegatorAddress,
  delegateAddress,
});

const balance = await token.decryptBalanceAs({
  delegatorAddress,
});
```

delegation 上链后需要等待 gateway 同步。太快读取可能遇到 `DelegationNotPropagatedError`。

## React Token Hooks

```tsx
const { data: balance } = useConfidentialBalance({ tokenAddress });
const { data: batch } = useConfidentialBalances({
  tokenAddresses: [tokenA, tokenB],
});
const shield = useShield({ tokenAddress, wrapperAddress });
const transfer = useConfidentialTransfer({ tokenAddress });
const unshield = useUnshield({ tokenAddress, wrapperAddress });

const tokenABalance = batch?.results.get(tokenA);
const tokenAError = batch?.errors.get(tokenA);
```

高层 hooks 会把 token objects 包装成 TanStack Query state、mutation state、cache invalidation、cached decryption 和 optimistic balance updates。

如果 confidential token 合约本身就是 wrapper，`wrapperAddress` 可以省略。接入 wrapped ERC20 registry 时，建议从 registry discovery 拿到明确的 wrapper/confidential pair，再把 wrapper address 传给 shield、unshield、unwrap、approve underlying 和 allowance hooks。

## 错误处理

Token workflow 常见错误：

| 错误或条件 | 典型处理 |
| --- | --- |
| public ERC20 balance 不足 | 展示当前 balance 和所需 amount |
| confidential balance 不足 | 刷新 confidential balance 并阻止 transfer |
| balance check unavailable | 要求用户授权 decrypt，或进入显式 `skipBalanceCheck` flow |
| 存在 pending unshield | 提供恢复 finalize |
| wrapper/registry 缺失 | 检查 chain id 和 registry address |
| 没有 encrypted balance | 捕获 `NoCiphertextError`，显示空状态，不要当作 `0n` |

`NoCiphertextError` 和 zero balance 不一样：

```ts
import { NoCiphertextError } from "@zama-fhe/sdk";

try {
  const balance = await token.balanceOf();
  // balance 可能是 0n，这是有效余额
} catch (error) {
  if (error instanceof NoCiphertextError) {
    // 用户从未 shield 过该 token
  }
}
```

零售 UI 不要静默跳过 balance checks。`skipBalanceCheck` 必须是显式产品决策。

## Token UX 检查清单

- shield 前显示 public ERC20 balance
- 授权后才显示 confidential balance
- approval 和 shield 要有独立 UI 状态
- 持久化并恢复 pending unshield finalization
- 区分 public ERC20 allowance 与 confidential operator approval
- 允许用户手动刷新 decrypted balances
- zero handle 直接渲染，不请求 decrypt
