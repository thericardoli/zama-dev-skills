# Sessions, Credentials, and Security Boundaries

This document supplements the official `Session model` and `Security model` content. It explains why the SDK prompts for wallet signatures, which data is persisted, how to configure TTLs, and which security boundaries matter in browsers and backends.

## Remember Three Things First

- The SDK protects read access to encrypted values. It does not hide transaction existence, call type, participant addresses, token addresses, gas, or timing.
- User decryption depends on two layers of material: a persisted FHE keypair and a session signature unlocked by an EIP-712 wallet signature.
- Browsers must not contain relayer API keys; if multi-threaded FHE is enabled, configure COOP/COEP; if CSP is enabled, allow workers and WASM.

## Two-Layer Authorization Model

The SDK's user decrypt flow does not regenerate keys every time. It has two layers:

| Layer | Data | Default Location | Lifecycle |
| --- | --- | --- | --- |
| FHE keypair | Public key + encrypted private key | `storage`, usually IndexedDB in browsers | Controlled by `keypairTTL` |
| Session signature | Wallet EIP-712 signature | `sessionStorage`, memory by default | Controlled by `sessionTTL` |

Flow:

1. User connects wallet.
2. SDK generates an FHE keypair.
3. SDK constructs EIP-712 typed data for the specified contract addresses.
4. User signs.
5. SDK derives an AES-GCM key from the signature material, encrypts the FHE private key, and stores it.
6. Subsequent decrypt operations in the current session reuse the cached signature and do not prompt again.

The plaintext FHE private key should exist only briefly in JS memory for a single operation; persistent storage contains the encrypted version.

## TTL Rules

Defaults in the `ZamaSDK` source:

| Option | Default | Notes |
| --- | --- | --- |
| `keypairTTL` | `2592000` seconds, or 30 days | FHE keypair lifetime; must be greater than 0 |
| `sessionTTL` | `2592000` seconds, or 30 days | Session signature lifetime |
| `registryTTL` | `86400` seconds, or 24 hours | Registry query cache |

Important boundaries:

- `keypairTTL: 0` throws because relayer connection requires a keypair.
- `keypairTTL` values above 365 days are capped at 365 days and emit a warning.
- `sessionTTL: 0` means the session signature is not cached; every operation that needs credentials will request a wallet signature.
- In core `ZamaSDKConfig`, `sessionTTL: "infinite"` means the session signature does not actively expire; use it only in high-trust environments, and remember the keypair is still constrained by `keypairTTL`. The current React `ZamaProviderProps` type is `number`; check local types before using a string on Provider props.
- If a numeric `sessionTTL` is greater than `keypairTTL`, the SDK clamps it to `keypairTTL`.

Example:

```ts
const sdk = new ZamaSDK({
  relayer,
  signer,
  storage,
  keypairTTL: 7 * 24 * 60 * 60,
  sessionTTL: 60 * 60,
});
```

## allow, isAllowed, revoke

The best UX is explicit authorization, not triggering a wallet signature as soon as the page loads.

```ts
await sdk.allow([tokenA, tokenB, vaultAddress]);
const ok = await sdk.credentials.isAllowed([tokenA]);
const values = await sdk.userDecrypt([{ handle, contractAddress: tokenA }]);
```

React:

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
  return <button onClick={() => allow.mutate([tokenAddress])}>Authorize balance view</button>;
}
```

One `allow()` call can cover multiple contract addresses. Pass all contracts the same page or product flow will read at once whenever possible, avoiding a new signature prompt for each additional address later.

Revoke:

```ts
await sdk.revokeSession();
await token.revoke(token.address);
sdk.dispose();
sdk.terminate();
```

- `revokeSession()` clears the session signature and related decrypt cache.
- `dispose()` cancels signer lifecycle subscriptions and does not close the relayer worker.
- `terminate()` calls `dispose()` and closes the `RelayerWeb` worker or `RelayerNode` pool.

## Wallet Lifecycle

`WagmiSigner` implements `subscribe()`, and `ZamaProvider` / `ZamaSDK` combine its lifecycle events and refresh related caches.

Custom signers and some viem/ethers wrappers need to handle this themselves:

```ts
wallet.on("disconnect", () => sdk.revokeSession());
wallet.on("accountsChanged", () => sdk.revokeSession());
```

Principles:

- Disconnect / lock: clear the current session.
- Account change: clear the old account session so the UI does not show authorization state for the wrong account.
- Chain change: credentials are isolated by address + chain; refresh queries and contract addresses after switching chains, and do not reuse handles.

## Browser Security

### API Key

Browsers must never contain:

```ts
auth: { __type: "ApiKeyHeader", value: "..." }
```

The frontend should only point to a proxy:

```ts
relayerUrl: "/api/relayer/11155111"
```

The server proxy injects `x-api-key` and adds login state, rate limiting, and CSRF protection as needed by the project.

### WASM, Workers, and CSP

`RelayerWeb` loads a pinned CDN WASM bundle in a Web Worker and performs SHA-384 integrity checks by default. Do not disable this in production:

```ts
const relayer = new RelayerWeb({
  getChainId: () => signer.getChainId(),
  transports,
  security: { integrityCheck: true },
});
```

If the application sets a strict CSP, it usually needs to allow:

```txt
worker-src blob:;
script-src 'self' 'wasm-unsafe-eval';
connect-src 'self' https://cdn.zama.org https://your-relayer-proxy.example;
```

### COOP/COEP

Cross-origin isolation headers are only required when enabling multi-threaded `threads` or a `SharedArrayBuffer` performance path:

```txt
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

Without these headers, the SDK tries to fall back to single-threaded execution. The result is lower performance and should not be treated as necessarily broken functionality.

## Data Visibility

FHE protects values, not all metadata.

Publicly visible:

- The transaction occurred
- Which contract and function were called
- Participant addresses
- Token address
- Gas, time, and block position
- Some clear amounts or public ERC20 transfer information in public/confidential boundary flows such as shield/unshield

Treat as confidential:

- Confidential transfer amount
- Plaintext balance corresponding to a confidential balance handle
- Encrypted state in custom contracts that has not been publicly authorized

If a product promises "fully hidden transaction relationships" or "shield amounts are also invisible", it needs additional protocol design; the SDK itself does not provide transaction graph privacy.

## Backend Security

Node backends can use the relayer API key directly:

```ts
auth: { __type: "ApiKeyHeader", value: process.env.RELAYER_API_KEY! }
```

But keep these rules:

- Private keys, mnemonics, and API keys must come from environment variables or a secret manager.
- Multi-user services must not share `memoryStorage`; use `asyncLocalStorage` or request-scoped SDKs.
- Do not log signed typed data, private keys, session signatures, or raw credentials.
- Call `sdk.terminate()` when long-lived processes exit.

## Security Checklist

- The frontend bundle contains no relayer API key.
- `ZamaProvider` is used only in client components.
- `useUserDecrypt` / `useConfidentialBalance` have explicit authorization gates.
- Every `handle` is paired with the correct `contractAddress`.
- `keypairTTL` and `sessionTTL` are deliberate product choices.
- Custom signers implement account/disconnect lifecycle, or revoke manually.
- CSP covers workers, WASM, and CDN access.
- Public decrypt is used only for values the contract explicitly makes public.
- Shield/unshield boundary amounts are not misdescribed in UX or privacy copy.
