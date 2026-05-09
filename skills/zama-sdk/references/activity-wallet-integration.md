# Activity Feeds, Wallets, and Exchange Integration

This document covers the product-integration parts of the official `Activity feeds`, `Wallet & exchange integration`, and `Operator approvals` content. It is intended for wallets, portfolio dashboards, exchanges, custodial backends, and dApps that need to display token history.

## What Wallets and Exchanges Need to Support

An ERC7984 confidential token is not a simple UI skin over a normal ERC20. Integrators usually need to support:

- Discovering mappings between public ERC20 tokens and confidential wrappers.
- Displaying metadata, public ERC20 balance, and confidential balance.
- Showing the user's own confidential balance through user decrypt.
- Building confidential transfers and encrypting the amount on the client.
- Supporting operator approval and `confidentialTransferFrom`.
- Supporting shield/unshield and resume after interrupted unshield.
- Parsing events into an activity feed.

You do not need to run FHE infrastructure yourself. The application calls the relayer, chain RPC, and wallet through the SDK.

## Key Privacy Boundaries

The amount in a confidential transfer is encrypted input; on-chain observers cannot see the transfer amount.

However, shield/unshield are boundary flows between public ERC20 and confidential tokens:

- Shield involves public ERC20 approval / transfer, and wrapper events also include clear amounts.
- Unshield eventually releases a plaintext public ERC20 amount, and finalize events include the clear amount.

Therefore wallet and exchange copy should not promise that "all amounts are always invisible." A more accurate statement is: after entering the confidential token, balances and confidential transfer amounts are encrypted; when entering or leaving the public ERC20 boundary, boundary amounts are visible according to public token rules.

## Registry Discovery

Use the SDK registry instead of hardcoding currently registered token addresses.

```ts
const result = await sdk.registry.getConfidentialToken(publicTokenAddress);

if (result?.isValid) {
  const token = sdk.createToken(result.confidentialTokenAddress);
}
```

Reverse lookup from confidential token to underlying public ERC20:

```ts
const result = await sdk.registry.getUnderlyingToken(confidentialTokenAddress);

if (result?.isValid) {
  console.log(result.tokenAddress);
}
```

List pairs with pagination:

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

React:

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

Core `sdk.registry.getConfidentialToken(...)` / `getUnderlyingToken(...)` returns a structured object that includes `isValid`. Low-level React registry hooks return tuples; first check whether the tuple's first item is `true`, then use `useIsConfidentialTokenValid` to verify that the current confidential token is still valid. A nonzero address found in the registry does not necessarily mean it is still usable.

## Balance Display

The first user decrypt triggers an EIP-712 signature. Wallet or exchange UIs should provide an explicit action, such as "View confidential balance".

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
      {isAllowing ? "Signing..." : "View confidential balance"}
    </button>
  );
}
```

Distinguish three states:

| State | Meaning | UI |
| --- | --- | --- |
| no ciphertext | The account has never shielded this token | Show an empty state and guide the user to shield |
| zero balance | An encrypted balance exists, but it is now `0n` | Show 0 |
| decrypt unavailable | User is not authorized, or relayer/auth failed | Show authorize or retry |

## Confidential Transfer

High-level API:

```ts
const token = sdk.createToken(confidentialTokenAddress);
const { txHash, receipt } = await token.confidentialTransfer(recipient, 500n);
```

React:

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

By default, the SDK tries to verify confidential balance before transfer. If there are no cached credentials, it throws `BalanceCheckUnavailableError` to avoid a surprise signature prompt. Pass `skipBalanceCheck: true` only when explicitly accepting on-chain revert risk.

## Operator Approval

Operator approval is similar to ERC20 approve/transferFrom, but it authorizes an encrypted token operator, not underlying public ERC20 allowance.

```ts
await token.approve(spender);

const expiry = Math.floor(Date.now() / 1000) + 24 * 60 * 60;
await token.approve(spender, expiry);

const approved = await token.isApproved(spender, owner);
```

Operator transfer:

```ts
await token.confidentialTransferFrom(owner, recipient, amount);
```

React:

```tsx
const approve = useConfidentialApprove({ tokenAddress });
const status = useConfidentialIsApproved({ tokenAddress, spender });
const transferFrom = useConfidentialTransferFrom({ tokenAddress });

await approve.mutateAsync({ spender, until: expiry });
await transferFrom.mutateAsync({ from: owner, to: recipient, amount });
```

UX notes:

- Approval should have a clear expiry; do not default to permanent authorization.
- Explain the risk that the operator can move confidential balance on the user's behalf.
- Make revoke or expiry modification easy to find.
- Public ERC20 allowance, confidential operator approval, and delegated decryption are three separate mechanisms.

## Delegated Decryption

Delegated decryption lets a delegate read encrypted values authorized by the delegator on a confidential contract. It is suitable for portfolio services, custodial reads, compliance reporting, or enterprise back offices.

```ts
await token.delegateDecryption({
  delegateAddress,
  expirationDate: new Date(Date.now() + 24 * 60 * 60 * 1000),
});

await token.revokeDelegation({ delegateAddress });
```

Batch:

```ts
const results = await Token.batchDelegateDecryption({
  tokens,
  delegateAddress,
  expirationDate,
});
```

Read:

```ts
const value = await readonlyToken.decryptBalanceAs({
  delegatorAddress,
});
```

Notes:

- Delegate cannot equal the delegator.
- Delegate cannot equal the token contract address.
- Expiration should be at least 1 hour in the future, otherwise the SDK throws `DelegationExpirationTooSoonError`.
- After delegation is on-chain, wait for gateway synchronization; reading too quickly may hit `DelegationNotPropagatedError`.
- Delegation authorizes reads only; it is not operator transfer approval.

## Activity Feed Pipeline

The SDK provides pure functions that turn raw logs into a renderable feed:

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

Core fields on `ActivityItem`:

| Field | Meaning |
| --- | --- |
| `type` | `"transfer"`, `"shield"`, `"unshield_requested"`, `"unshield_started"`, `"unshield_finalized"` |
| `direction` | `"incoming"`, `"outgoing"`, `"self"` |
| `amount` | Clear amount or encrypted handle; `decryptedValue` is filled after decryption |
| `from` / `to` | Event participant addresses |
| `metadata` | tx hash, block number, log index |
| `rawEvent` | Original decoded event |

React hook:

```tsx
const { data: feed, isLoading } = useActivityFeed({
  tokenAddress,
  userAddress,
  logs,
  decrypt: true,
});
```

In source, `decrypt` defaults to `true`. Set `decrypt: false` to classify events only, without decrypting encrypted amounts. This fits public activity lists, unauthorized states, or performance previews.

## Event Decoders

If you only need lower-level event parsing:

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

Event objects are discriminated by `eventName`:

```ts
const events = decodeOnChainEvents(receipt.logs);

for (const event of events) {
  if (event.eventName === "ConfidentialTransfer") {
    console.log(event.from, event.to, event.encryptedAmountHandle);
  }
}
```

ACL delegation events are not in `TOKEN_TOPICS`. They are emitted by the ACL contract and must be queried separately with `ACL_TOPICS`.

## Wallet/Exchange UX Checklist

- Check `isValid` on registry results.
- Do not hardcode the currently registered official token addresses; allow registry refresh.
- Clearly distinguish public ERC20 balance from confidential balance.
- Trigger the first decrypt from a user click.
- Display `NoCiphertextError` separately from `0n`.
- Make clear that public boundary amounts are visible for shield/unshield.
- Show true operator/approval/decryption status before transfer.
- Allow resume when a pending unshield exists.
- Support pagination or an indexer for activity feeds; do not scan the whole chain at once.
- Show expiry, delegate, and revoke action for delegation status.
