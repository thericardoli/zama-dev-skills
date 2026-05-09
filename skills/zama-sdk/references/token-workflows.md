# ERC7984 Token Workflows

This document applies to ERC7984 confidential token UIs, wrapped ERC20 flows, registry discovery, shield token, private transfer, unshield token, and balance checks. It follows the official Guides structure: shield, confidential transfers, unshield, balance checks, and error handling.

## When to Use the Token API

When the target contract is an ERC7984 confidential token or wrapper, use `Token`, `ReadonlyToken`, and token hooks.

Do not use the token API for arbitrary FHE contracts such as auctions, vaults, private counters, or voting contracts. Read `custom-contracts.md` for those scenarios.

## Create a Token Object

The first argument to `sdk.createToken(address, wrapper?)` is the **ERC7984 confidential token contract address**, not the underlying public ERC20 address.

```ts
const token = sdk.createToken(confidentialTokenAddress);
```

The returned value is a `Token` instance. `Token` extends `ReadonlyToken`, so it includes read-only capabilities such as metadata, balance, allow/decrypt, and write operations such as shield, confidential transfer, operator approval, unshield, and delegation.

Address roles:

| Address | Meaning | Where to Pass It |
| --- | --- | --- |
| `publicTokenAddress` | Underlying public ERC20, such as ordinary USDC/ERC20 | Do not pass to `createToken`; use for registry lookup, public balance display, or low-level ERC20 reads/writes |
| `confidentialTokenAddress` | ERC7984 confidential token contract | First argument to `sdk.createToken(confidentialTokenAddress)` |
| `wrapperAddress` | Wrapper contract that wraps/unwraps public ERC20; in some deployments it may be the same as the confidential token address | Second argument to `sdk.createToken(confidentialTokenAddress, wrapperAddress)` |

Pass the wrapper explicitly:

```ts
const token = sdk.createToken(confidentialTokenAddress, wrapperAddress);
```

If `wrapperAddress` is omitted, the SDK treats the wrapper as `confidentialTokenAddress`. This only fits deployments where the confidential token contract is itself the wrapper; wrapped ERC20 projects should usually pass the wrapper address discovered from the registry explicitly.

Read-only:

```ts
const readonlyToken = sdk.createReadonlyToken(confidentialTokenAddress);
```

## Shield Flow

Public ERC20 to confidential token:

```ts
await token.shield(1000n);
```

Options:

| Option | Meaning |
| --- | --- |
| `approvalStrategy` | `"exact"`, `"max"`, or `"skip"` |
| `to` | Confidential token recipient |
| `onApprovalSubmitted` | Public approval tx hash callback |
| `onShieldSubmitted` | Shield tx hash callback |

The SDK handles public ERC20 balance checks, approval, and the wrapper `wrap` transaction. It checks the public ERC20 balance first. If the public balance is insufficient, it throws `InsufficientERC20BalanceError`.

Note: shield is the boundary operation where public ERC20 enters a confidential token. Public ERC20 transfers/approvals and boundary amounts in wrapper events are usually visible; only balances and subsequent confidential transfer amounts inside the confidential token follow the FHE privacy flow.

## Check Balances

Decrypt the balance:

```ts
await token.allow();
const balance = await token.balanceOf();
```

Read the encrypted handle:

```ts
const handle = await token.confidentialBalanceOf(owner);
```

Use `confidentialBalanceOf` when the UI only needs the handle, or when you need custom decrypt orchestration.

React:

```tsx
const { data: balance, isLoading } = useConfidentialBalance({ tokenAddress });
```

The current React hook reads the current signer's balance. To display an arbitrary owner, use the core API:

```ts
const rt = sdk.createReadonlyToken(confidentialTokenAddress);
const balance = await rt.balanceOf(owner);
const handle = await rt.confidentialBalanceOf(owner);
```

The first decrypt may require a wallet signature. Later cached credentials and decrypt cache avoid repeated prompts until TTL, revoke, account change, or chain change.

## Confidential Transfer

```ts
await token.confidentialTransfer(recipient, 500n);
```

Options:

| Option | Meaning |
| --- | --- |
| `skipBalanceCheck` | Skip the local confidential balance decrypt check |
| `onEncryptComplete` | Called after FHE encryption completes |
| `onTransferSubmitted` | Transfer tx callback |

The SDK encrypts the amount on the client and then writes the transfer. By default, it decrypts the confidential balance before transfer to perform a check. If the wallet cannot sign decrypt credentials, smart wallet flows may need `skipBalanceCheck`, but they must accept the risk of an on-chain revert.

React:

```tsx
const transfer = useConfidentialTransfer({ tokenAddress });
await transfer.mutateAsync({ to: recipient, amount: 500n });
```

## Operator Transfer

```ts
await token.confidentialTransferFrom(from, to, 500n);
```

Requires confidential operator approval.

## Confidential Approval

```ts
await token.approve(spender);
await token.approve(spender, expiryTimestamp);
const ok = await token.isApproved(spender);
```

This is confidential token operator approval, not public ERC20 allowance and not delegated decryption. The default `approve(spender)` uses a roughly 1-hour window; production UIs should show the spender, expiry, and revoke/update entry points.

React:

```tsx
const approve = useConfidentialApprove({ tokenAddress });
const approved = useConfidentialIsApproved({ tokenAddress, spender });
const transferFrom = useConfidentialTransferFrom({ tokenAddress });

await approve.mutateAsync({ spender, until: expiryTimestamp });
await transferFrom.mutateAsync({ from, to, amount });
```

## Unshield Flow

Confidential token to public ERC20:

```ts
await token.unshield(500n);
```

It orchestrates:

1. Phase 1 unwrap/burn request
2. Public decrypt proof retrieval
3. Phase 2 finalize

Options:

| Option | Meaning |
| --- | --- |
| `skipBalanceCheck` | Skip confidential balance check |
| `onUnwrapSubmitted` | Phase 1 tx callback |
| `onFinalizing` | Proof/finalize phase starts |
| `onFinalizeSubmitted` | Phase 2 tx callback |

Resume an interrupted flow:

```ts
await token.resumeUnshield(unwrapTxHash);
```

Storage helpers:

```ts
import { loadPendingUnshield, clearPendingUnshield } from "@zama-fhe/sdk";

const pending = await loadPendingUnshield(storage, wrapperAddress);
if (pending) {
  await token.resumeUnshield(pending);
  await clearPendingUnshield(storage, wrapperAddress);
}
```

React:

```tsx
const unshield = useUnshield({ tokenAddress, wrapperAddress });
await unshield.mutateAsync({ amount: 500n });
```

Pending unshield UX matters because unshield spans multiple phases. Persist enough state to let users resume finalize.

Unshield everything:

```ts
await token.unshieldAll();
```

React:

```tsx
const unshieldAll = useUnshieldAll({ tokenAddress, wrapperAddress });
await unshieldAll.mutateAsync();
```

If the product needs full manual control over the two-phase flow, use the lower-level `unwrap` / `finalizeUnwrap`:

```ts
const unwrap = await token.unwrap(500n);
const event = findUnwrapRequested(unwrap.receipt.logs);
if (event) {
  await token.finalizeUnwrap(event.encryptedAmount);
}
```

## Underlying ERC20 Approval

```ts
await token.approveUnderlying();
await token.approveUnderlying(1000n);
```

Commonly used before `shield(..., { approvalStrategy: "skip" })`, or when the product wants approval as a separate step.

React:

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

## ReadonlyToken Read-Only Interface

```ts
const rt = sdk.createReadonlyToken(tokenAddress);
```

Common methods:

| Method | Meaning |
| --- | --- |
| `balanceOf(owner?)` | Decrypt confidential balance |
| `confidentialBalanceOf(owner?)` | Encrypted balance handle |
| `name()` | Token name |
| `symbol()` | Token symbol |
| `decimals()` | Decimals |
| `isConfidential()` | ERC7984 support |
| `isWrapper()` | Wrapper detection |
| `underlyingToken()` | Underlying public ERC20 |
| `allowance(wrapper, owner?)` | Public ERC20 allowance |
| `allow()` / `revoke()` / `isAllowed()` | Decrypt session management |

Import zero-handle helpers from the SDK:

```ts
import { isZeroHandle, ZERO_HANDLE } from "@zama-fhe/sdk";
```

Batch balances:

```ts
const tokens = addresses.map((address) => sdk.createReadonlyToken(address));
await ReadonlyToken.allow(...tokens);
const { results, errors } = await ReadonlyToken.batchBalancesOf(tokens, owner);
```

A single token failure does not reject the entire batch.

## Registry

```ts
const pairs = await sdk.registry.listPairs({ page: 1 });
const confidential = await sdk.registry.getConfidentialToken(publicToken);
const publicToken = await sdk.registry.getUnderlyingToken(confidentialToken);
```

Custom registry:

```ts
const registry = sdk.createWrappersRegistry({
  [31337]: "0xRegistry",
});
```

## Delegated Decryption

Delegated decryption is "authorize reads", not "authorize transfers".

```ts
await token.delegateDecryption({
  delegateAddress,
  expirationDate: new Date(Date.now() + 24 * 60 * 60 * 1000),
});

await token.revokeDelegation({ delegateAddress });
```

Read delegation status or decrypt a balance as a delegate:

```ts
const delegated = await token.isDelegated({
  delegatorAddress,
  delegateAddress,
});

const balance = await token.decryptBalanceAs({
  delegatorAddress,
});
```

After delegation is on-chain, wait for gateway synchronization. Reading too quickly may produce `DelegationNotPropagatedError`.

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

High-level hooks wrap token objects into TanStack Query state, mutation state, cache invalidation, cached decryption, and optimistic balance updates.

If the confidential token contract is itself the wrapper, `wrapperAddress` can be omitted. When integrating with a wrapped ERC20 registry, prefer discovering the explicit wrapper/confidential pair from the registry, then pass the wrapper address to shield, unshield, unwrap, approve underlying, and allowance hooks.

## Error Handling

Common token workflow errors:

| Error or Condition | Typical Handling |
| --- | --- |
| Insufficient public ERC20 balance | Show the current balance and required amount |
| Insufficient confidential balance | Refresh the confidential balance and block transfer |
| Balance check unavailable | Ask the user to authorize decrypt, or enter an explicit `skipBalanceCheck` flow |
| Pending unshield exists | Offer resume/finalize |
| Missing wrapper/registry | Check chain id and registry address |
| No encrypted balance | Catch `NoCiphertextError`, show an empty state, and do not treat it as `0n` |

`NoCiphertextError` is not the same as zero balance:

```ts
import { NoCiphertextError } from "@zama-fhe/sdk";

try {
  const balance = await token.balanceOf();
  // balance may be 0n, which is a valid balance
} catch (error) {
  if (error instanceof NoCiphertextError) {
    // The user has never shielded this token
  }
}
```

Retail UIs should not silently skip balance checks. `skipBalanceCheck` must be an explicit product decision.

## Token UX Checklist

- Show the public ERC20 balance before shield.
- Show the confidential balance only after authorization.
- Give approval and shield independent UI states.
- Persist and resume pending unshield finalization.
- Distinguish public ERC20 allowance from confidential operator approval.
- Let users manually refresh decrypted balances.
- Render zero handles directly without requesting decrypt.
