# Errors, Events, and Observability

This document combines `Handle errors`, `Error types`, `Event decoders`, and the `errors/*` and `events/*` source modules. The goal is to help applications turn failures into recoverable UI states instead of showing only a raw error.

## Error Handling Entry Points

All typed SDK errors extend `ZamaError` and include a stable `.code` string.

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
    showError("Encryption failed. Please try again.");
    return;
  }

  if (error instanceof ZamaError) {
    showError(error.message);
    return;
  }

  throw error;
}
```

`matchZamaError` fits UI layers well:

```ts
const message = matchZamaError(error, {
  SIGNING_REJECTED: () => "The user rejected the wallet signature",
  INSUFFICIENT_CONFIDENTIAL_BALANCE: (e) => `Insufficient confidential balance: ${e.message}`,
  INSUFFICIENT_ERC20_BALANCE: (e) => `Insufficient public ERC20 balance: ${e.message}`,
  BALANCE_CHECK_UNAVAILABLE: () => "Authorize balance viewing first, or explicitly skip the balance check",
  RELAYER_REQUEST_FAILED: (e) => `Relayer request failed: ${e.message}`,
  _: (e) => (e instanceof Error ? e.message : "Unknown error"),
});
```

## Common Error Codes

| Error class | Code | Common Scenario | Recommended Handling |
| --- | --- | --- | --- |
| `SigningRejectedError` | `SIGNING_REJECTED` | User rejects an EIP-712 signature or transaction | Show retry; do not treat as a system error |
| `SigningFailedError` | `SIGNING_FAILED` | Wallet, hardware wallet, or RPC signing failure | Ask the user to check wallet connection |
| `EncryptionFailedError` | `ENCRYPTION_FAILED` | FHE encryption worker/WASM failure | Check workers, CSP, and input types |
| `DecryptionFailedError` | `DECRYPTION_FAILED` | User/public decrypt failure | Check ACL, handle, and pending unshield state |
| `ApprovalFailedError` | `APPROVAL_FAILED` | Public ERC20 approval failure | Check gas, allowance, and token behavior |
| `TransactionRevertedError` | `TRANSACTION_REVERTED` | Contract write reverted | Decode the revert reason and refresh on-chain state |
| `InvalidKeypairError` | `INVALID_KEYPAIR` | Relayer rejects the keypair | Revoke the session and authorize again |
| `KeypairExpiredError` | `KEYPAIR_EXPIRED` | `keypairTTL` expired | Run `allow()` again |
| `NoCiphertextError` | `NO_CIPHERTEXT` | Account has never had an encrypted balance for this token | Show an empty state; not equivalent to 0 |
| `RelayerRequestFailedError` | `RELAYER_REQUEST_FAILED` | Relayer/proxy 401, 403, 5xx, or network failure | Check `relayerUrl`, API key, and proxy |
| `ConfigurationError` | `CONFIGURATION` | Import path, chain, worker, or registry configuration error | Check initialization config |
| `InsufficientConfidentialBalanceError` | `INSUFFICIENT_CONFIDENTIAL_BALANCE` | Insufficient balance before transfer/unshield | Show the shortfall and block submission |
| `InsufficientERC20BalanceError` | `INSUFFICIENT_ERC20_BALANCE` | Insufficient public balance before shield | Guide top-up or reduce amount |
| `BalanceCheckUnavailableError` | `BALANCE_CHECK_UNAVAILABLE` | No cached credentials; SDK avoids triggering a surprise signature | Provide an authorization button, or explicitly use `skipBalanceCheck` |
| `ERC20ReadFailedError` | `ERC20_READ_FAILED` | Failed to read public ERC20 balance/allowance | Check RPC and token address |
| `DelegationSelfNotAllowedError` | `DELEGATION_SELF_NOT_ALLOWED` | Delegate equals current user | Ask for a different delegate |
| `DelegationDelegateEqualsContractError` | `DELEGATION_DELEGATE_EQUALS_CONTRACT` | Delegate equals contract address | Ask for a different delegate |
| `DelegationExpiryUnchangedError` | `DELEGATION_EXPIRY_UNCHANGED` | New expiry equals the existing value | Do not send a transaction; indicate it is already the current setting |
| `DelegationNotFoundError` | `DELEGATION_NOT_FOUND` | Revoking a nonexistent delegation | Refresh state |
| `DelegationExpiredError` | `DELEGATION_EXPIRED` | Delegation has expired | Authorize again |
| `DelegationCooldownError` | `DELEGATION_COOLDOWN` | Repeated delegate/revoke in the same block | Wait for the next block |
| `DelegationContractIsSelfError` | `DELEGATION_CONTRACT_IS_SELF` | Contract equals caller | Fix parameters |
| `DelegationExpirationTooSoonError` | `DELEGATION_EXPIRATION_TOO_SOON` | Expiry is less than 1 hour away | Choose a later expiry |
| `DelegationNotPropagatedError` | `DELEGATION_NOT_PROPAGATED` | Delegation is on-chain but the gateway has not synchronized yet | Wait 1-2 minutes and retry |
| `AclPausedError` | `ACL_PAUSED` | ACL contract is paused | Stop related actions and show service status |

## No Ciphertext vs Zero Balance

This is one of the easiest UI states to confuse.

```ts
import { NoCiphertextError } from "@zama-fhe/sdk";

try {
  const balance = await token.balanceOf();
  renderBalance(balance); // 0n is a valid balance
} catch (error) {
  if (error instanceof NoCiphertextError) {
    renderEmptyState("No confidential balance yet. Shield first.");
  }
}
```

`NoCiphertextError` means there is no encrypted balance handle on-chain; `0n` means a handle exists and decrypts to 0.

## Relayer / Worker Status

`RelayerWeb` has initialization status:

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

Common states:

- `idle`: not initialized yet.
- `initializing`: loading worker/WASM.
- `ready`: available.
- `error`: initialization failed; read `initError`.

## SDK Lifecycle Events

`ZamaSDK` supports `onEvent`, which is useful for debugging and telemetry. Events do not include private keys or plaintext secrets, but still avoid blindly sending full event objects to third-party logs.

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

Typical events include encryption start/end/error, transaction submitted/error, delegation submitted, session revoked, and similar lifecycle events. The precise event enum is defined in `node_modules/@zama-fhe/sdk/dist/esm/index.d.ts` or `packages/sdk/src/events/sdk-events.ts`.

## Event Decoders

The SDK provides framework-agnostic raw log decoders. They work with logs returned by viem, ethers, or a custom provider as long as the logs include `topics` and `data`.

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

Fetch token events:

```ts
const logs = await publicClient.getLogs({
  address: tokenAddress,
  topics: [TOKEN_TOPICS],
  fromBlock,
  toBlock: "latest",
});

const events = decodeOnChainEvents(logs);
```

Event objects are discriminated by `eventName`:

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

Convenience finders:

```ts
const wrapped = findWrapped(receipt.logs);
const unwrap = findUnwrapRequested(receipt.logs);
```

Query ACL delegation events from the ACL contract:

```ts
const logs = await publicClient.getLogs({
  address: aclAddress,
  topics: [ACL_TOPICS],
  fromBlock,
  toBlock: "latest",
});

const aclEvents = decodeAclEvents(logs);
```

## Activity Feed Helpers

Activity feeds are a layer over event decoders:

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

`extractEncryptedHandles` skips zero handles and de-duplicates. `applyDecryptedValues` expects decrypted values to be `bigint`, because activity amounts are token amounts.

## Troubleshooting Strategy

Debug by layer:

1. Is the import path correct?
2. Do chain id, transport preset, and contract address match?
3. Does the relayer proxy return 401/403/5xx?
4. Are worker/WASM/CSP settings blocking initialization?
5. Does the wallet support EIP-712 signing?
6. Does the ACL allow the current user/delegate to decrypt?
7. Has the session/keypair TTL expired?
8. Do the handle and `contractAddress` come from the same contract?
9. Has the token flow mixed up public ERC20 allowance, confidential operator approval, and delegated decrypt?
