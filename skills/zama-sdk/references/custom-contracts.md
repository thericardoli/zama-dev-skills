# Custom Contracts

This document applies to non-ERC7984-token FHEVM contracts such as vaults, auctions, voting, private counters, matching engines, and application-specific encrypted state.

These scenarios use the lower-level **Encrypt & decrypt** model: token hooks handle encrypted token flows automatically, while custom contracts must explicitly use `useEncrypt`, contract writes, and `useUserDecrypt`.

## End-to-End Flow

1. Read the current signer address and chain id.
2. Encrypt plaintext values with the address of the contract that will consume the input.
3. Convert encrypted handles and the input proof to hex.
4. Call the Solidity function that accepts encrypted external input and `bytes proof`.
5. If the UI needs to show the result, read the encrypted handle back from the contract.
6. Confirm that the ACL lets the user or delegate decrypt that handle.
7. Use `sdk.userDecrypt` for private values and `sdk.publicDecrypt` for public reveal flows.

## Solidity Shape to Match

A typical Solidity function:

```solidity
function submit(externalEuint64 amount, bytes calldata inputProof) external {
    euint64 value = FHE.fromExternal(amount, inputProof);
    _balances[msg.sender] = FHE.add(_balances[msg.sender], value);
    FHE.allowThis(_balances[msg.sender]);
    FHE.allow(_balances[msg.sender], msg.sender);
}
```

The `contractAddress` used during SDK encryption must be the address of the contract that calls `FHE.fromExternal`.

## Encrypt Inputs

```ts
import { bytesToHex } from "viem";

const userAddress = await sdk.signer.getAddress();

const encrypted = await sdk.relayer.encrypt({
  values: [
    { type: "euint64", value: amount },
    { type: "ebool", value: true },
  ],
  contractAddress,
  userAddress,
});

const encryptedAmount = bytesToHex(encrypted.handles[0]!);
const encryptedFlag = bytesToHex(encrypted.handles[1]!);
const inputProof = bytesToHex(encrypted.inputProof);
```

Supported value shapes:

| FHE type | JS value |
| --- | --- |
| `ebool` | `boolean` or `bigint` 0/1 |
| `euint8` | `bigint` |
| `euint16` | `bigint` |
| `euint32` | `bigint` |
| `euint64` | `bigint` |
| `euint128` | `bigint` |
| `euint256` | `bigint` |
| `eaddress` | `0x...` address |

If the encryption result has empty handles, first check that `contractAddress` and `userAddress` are valid addresses, and confirm the wallet is connected before calling encrypt.

## Write the Contract

```ts
const txHash = await sdk.signer.writeContract({
  address: contractAddress,
  abi,
  functionName: "submit",
  args: [encryptedAmount, inputProof],
});

await sdk.signer.waitForTransactionReceipt(txHash);
```

Handles and the input proof produced by the same `encrypt` call must be used together. Do not mix handles and proofs from different encrypt calls.

## Read Handles

After the transaction completes, read the exposed handle from the contract:

```ts
const handle = (await sdk.signer.readContract({
  address: contractAddress,
  abi,
  functionName: "balanceOf",
  args: [userAddress],
})) as `0x${string}`;
```

If a handle is already a `0x...` string, store it directly. Only `Uint8Array` values need `bytesToHex`.

## User Decryption

Private decrypt requires contract-side ACL permission and wallet credentials:

```ts
await sdk.allow([contractAddress]);

const result = await sdk.userDecrypt([
  { handle, contractAddress },
]);

const clearBalance = result[handle] as bigint;
```

Rules:

- Every handle must include the `contractAddress` that owns it.
- `contractAddress` is the contract that owns the encrypted handle, which is not necessarily the contract currently being called.
- Zero handles can be displayed as 0 directly; they do not need a relayer request.
- Credentials are cached by requester, chain, contracts, and TTL.
- Authorization must be refreshed after account or chain changes.

React query pattern:

```tsx
const { mutate: allow, isPending: isAllowing } = useAllow();
const { data: isAllowed } = useIsAllowed({ contractAddresses: [contractAddress] });

const { data, isPending } = useUserDecrypt(
  { handles: [{ handle, contractAddress }] },
  { enabled: !!isAllowed },
);
```

When `isAllowed` is false, provide an explicit authorize button. This prevents the decrypt query from triggering a wallet prompt during page render.

## One-Time Pre-Authorization

A common app pattern is to render children only after authorization has been cached:

```tsx
function UserDecryptionGate({
  contracts,
  children,
}: {
  contracts: `0x${string}`[];
  children: React.ReactNode;
}) {
  const { mutate: allow, isPending } = useAllow();
  const { data: allowed } = useIsAllowed({ contractAddresses: contracts });

  if (allowed) return <>{children}</>;

  return (
    <button onClick={() => allow(contracts)} disabled={isPending}>
      {isPending ? "Signing..." : "Authorize decryption"}
    </button>
  );
}
```

After authorization completes, nested `useUserDecrypt` or `useConfidentialBalance` calls can reuse the cached credentials.

## Multi-Contract Handles

`useUserDecrypt` and `sdk.userDecrypt` can process values from multiple contracts. The SDK groups them by contract address and sends one decrypt request per group:

```tsx
const handles = [
  { handle: handleA1, contractAddress: tokenA },
  { handle: handleA2, contractAddress: tokenA },
  { handle: handleB1, contractAddress: tokenB },
];

const { data } = useUserDecrypt(
  { handles },
  { enabled: handles.length > 0 && !!allowed },
);
```

Returned data is keyed by handle.

In the example above, `allowed` should come from `useIsAllowed({ contractAddresses: [tokenA, tokenB] })` or an equivalent authorization gate. The React SDK's `useUserDecrypt` requires callers to pass `enabled` explicitly by default, preventing page render from triggering a wallet signature immediately.

## Persistent Cache

Decrypted values are cached and isolated by signer and contract. Depending on the storage backend, the cache can survive page reloads. Revoke flows, wallet disconnects, account changes, chain changes, or explicit cache clearing clear the cache.

## Public Decryption

Public decrypt is only for values that the contract explicitly allows to be public. On the Solidity side, the target encrypted value usually needs to be authorized for public decryption, for example with `FHE.makePubliclyDecryptable(value)`, after which the off-chain relayer/KMS returns the clear value and proof. `allowForDecryption` is the low-level ACL contract interface; business contracts should not write this as `FHE.allowForDecryption(...)`.

```ts
const {
  clearValues,
  abiEncodedClearValues,
  decryptionProof,
} = await sdk.publicDecrypt([handle]);
```

`decryptionProof` and `abiEncodedClearValues` are usually passed to an on-chain finalize callback where the contract verifies the signature. They must precisely match the callback ABI; do not assume a proof generated for one ABI can be used with another ABI.

If the goal is only to let the current user read their own value, do not use public decrypt. Use `sdk.userDecrypt([{ handle, contractAddress }])` and authorize the user through the contract ACL.

## Delegated Decryption

Delegated decrypt lets one account authorize another account to decrypt specific handles or values within a specific contract scope. It is suitable for dashboards, service agents, custodial views, or delegated portfolio reads.

High-level entry points include:

- `sdk.delegatedCredentials`
- `relayer.createDelegatedUserDecryptEIP712`
- `relayer.delegatedUserDecrypt`
- React delegation hooks

Delegation is not ERC20 allowance. It has its own delegator, delegate, contract, handle, expiry, and revocation model.

## Events and Activity Decoding

The SDK exports event/activity helpers for token and registry flows. For custom contracts, prefer normal viem/ethers ABI decoding; use SDK decoders only when the event format belongs to an SDK token or activity abstraction.

## Common Contract Integration Mistakes

- Encrypting with a proxy/router address while `FHE.fromExternal` actually executes in another contract.
- Pairing a handle from one contract with another `contractAddress` during decryption.
- Forgetting `FHE.allowThis` after writing a new handle.
- Forgetting `FHE.allow(handle, user)` for values the user needs to decrypt.
- Calling `bytesToHex` again on a handle that is already `0x...`.
- Using `publicDecrypt` for a user-private value.
- Automatically triggering `userDecrypt` before the user is connected or authorized.
