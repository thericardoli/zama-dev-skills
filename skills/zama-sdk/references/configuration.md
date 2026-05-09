# Configuration

Every SDK instance needs three core parts: a relayer runtime, a signer, and a storage backend. This document follows the structure of the official configuration guide and adds notes on authentication, browser/server boundaries, artifact caching, web extensions, and cleanup.

## Package Exports

Core SDK:

| Import path | Purpose |
| --- | --- |
| `@zama-fhe/sdk` | `ZamaSDK`, `RelayerWeb`, network presets, storage, `Token`, `ReadonlyToken`, builders, errors |
| `@zama-fhe/sdk/node` | `RelayerNode`, worker options, `asyncLocalStorage` |
| `@zama-fhe/sdk/cleartext` | `RelayerCleartext`, `hardhatCleartextConfig`, `hoodiCleartextConfig` |
| `@zama-fhe/sdk/viem` | `ViemSigner` and viem helpers |
| `@zama-fhe/sdk/ethers` | `EthersSigner` and ethers helpers |
| `@zama-fhe/sdk/query` | TanStack Query option factories and query keys |

React SDK:

| Import path | Purpose |
| --- | --- |
| `@zama-fhe/react-sdk` | `ZamaProvider`, hooks, and React-oriented re-exports |
| `@zama-fhe/react-sdk/wagmi` | `WagmiSigner` |

Import from the most specific export path whenever possible. Common mistakes include importing `RelayerNode` from the browser main entry point, or importing `WagmiSigner` from a non-wagmi path.

## Dependency Selection

| Project | Install |
| --- | --- |
| Browser / vanilla TS + viem | `@zama-fhe/sdk viem` |
| Browser / vanilla TS + ethers | `@zama-fhe/sdk ethers` |
| React / wagmi | `@zama-fhe/react-sdk @zama-fhe/sdk @tanstack/react-query viem wagmi` |
| React / Vite / TypeScript | Previous row plus `react react-dom @vitejs/plugin-react vite typescript @types/react @types/react-dom` |
| Node backend | `@zama-fhe/sdk viem` or `@zama-fhe/sdk ethers` |

Do not upgrade SDK packages blindly, and do not write nonexistent old versions. For new projects, first query the real published versions:

```bash
pnpm view @zama-fhe/sdk version
pnpm view @zama-fhe/react-sdk version
pnpm view wagmi version
pnpm view viem version
```

Then install the same generation of `@zama-fhe/sdk` and `@zama-fhe/react-sdk`. If the project already has a lockfile, prefer keeping the current major version and inspect the installed type files to confirm the API.

Verified starting point for a local React/wagmi demo:

| Package | Version Strategy |
| --- | --- |
| `@zama-fhe/sdk` / `@zama-fhe/react-sdk` | Same release version, for example `3.0.0` |
| `wagmi` | When using the current stable v2, verify that `@zama-fhe/react-sdk/wagmi` can bundle |
| `viem` | Use the compatible version required by wagmi |
| `@types/react` / `@types/react-dom` | Must be installed explicitly in TypeScript React projects |

If `@zama-fhe/react-sdk/wagmi` fails during build with an error like `"watchConnection" is not exported by "wagmi/actions"`, do not patch `node_modules`; use the custom `GenericSigner` fallback instead.

## Network Presets

Common presets exposed by the SDK:

| Preset | Chain ID | Typical Use |
| --- | --- | --- |
| `MainnetConfig` | `1` | Ethereum Mainnet |
| `SepoliaConfig` | `11155111` | Sepolia testnet |
| `HardhatConfig` | `31337` | Local Hardhat node |

Presets provide the contract and network metadata required by the SDK, including chain id, relayer URL, gateway address, ACL address, and KMS verifier address. Use a preset as the baseline, then override the project's own RPC/proxy URL.

```ts
const transports = {
  [SepoliaConfig.chainId]: {
    ...SepoliaConfig,
    network: process.env.NEXT_PUBLIC_SEPOLIA_RPC_URL!,
    relayerUrl: "/api/relayer/11155111",
  },
};
```

## Browser Transport

Browser code that needs relayer authentication should configure a proxy URL:

```ts
const relayer = new RelayerWeb({
  getChainId: () => signer.getChainId(),
  transports: {
    [SepoliaConfig.chainId]: {
      ...SepoliaConfig,
      network: "https://ethereum-sepolia-rpc.publicnode.com",
      relayerUrl: "/api/relayer/11155111",
    },
  },
});
```

The proxy forwards requests to the actual relayer endpoint and injects private credentials on the server.

## Node Transport

Server-side code can read private environment variables:

```ts
const relayer = new RelayerNode({
  getChainId: () => signer.getChainId(),
  transports: {
    [SepoliaConfig.chainId]: {
      ...SepoliaConfig,
      network: process.env.SEPOLIA_RPC_URL!,
      auth: { __type: "ApiKeyHeader", value: process.env.RELAYER_API_KEY! },
    },
  },
});
```

Use this pattern only on the server. RPC URLs, relayer URLs, private keys, mnemonics, and API keys should all be managed per environment.

## Authentication

The official documentation describes two authentication strategies:

| Strategy | Use Case | Secret Location |
| --- | --- | --- |
| Backend proxy | Browser apps and dApps | Server only |
| Direct API key | Node scripts, backend services, prototyping | Transport `auth` field |

A browser app should not include `auth` in frontend runtime config. Point `relayerUrl` at a same-origin or trusted backend endpoint:

```ts
const relayer = new RelayerWeb({
  getChainId: () => signer.getChainId(),
  transports: {
    [SepoliaConfig.chainId]: {
      ...SepoliaConfig,
      relayerUrl: "https://your-app.com/api/relayer/11155111",
      network: "https://sepolia.infura.io/v3/YOUR_KEY",
    },
  },
});
```

Server-side code can pass:

```ts
auth: { __type: "ApiKeyHeader", value: process.env.RELAYER_API_KEY! }
```

Supported auth shapes:

| Method | Shape | Header or Transport Behavior |
| --- | --- | --- |
| `ApiKeyHeader` | `{ __type: "ApiKeyHeader", value: "key" }` | Sends `x-api-key` |
| `ApiKeyCookie` | `{ __type: "ApiKeyCookie", value: "key" }` | Sets a cookie |
| `BearerToken` | `{ __type: "BearerToken", token: "jwt" }` | Sends `Authorization: Bearer ...` |

When using a browser proxy, add CSRF protection if the application has login state or state-changing proxy behavior.

## Relayer API Key Acquisition and Hosting

The upstream documentation divides relayer integration into two categories:

| Mode | Suitable For | Notes |
| --- | --- | --- |
| Zama-hosted Relayer | Mainnet/testnet applications that do not want to operate their own relayer | Requires applying for an API key and is billed according to usage/protocol rules |
| Self-hosted Relayer | Teams with independent operations, billing, or gateway wallet requirements | Requires deploying, monitoring, and maintaining the relayer yourself |

After receiving a Zama-hosted key, still choose either a browser proxy or a server-side direct key as described above. Do not put the issued key into `NEXT_PUBLIC_`, `VITE_`, or any frontend bundle.

If you suspect the key has leaked, stop using it, rotate the configuration, and contact Zama support.

## Multi-Chain Configuration

Provide one transport per supported chain:

```ts
const relayer = new RelayerWeb({
  getChainId: () => signer.getChainId(),
  transports: {
    [SepoliaConfig.chainId]: {
      ...SepoliaConfig,
      network: sepoliaRpcUrl,
      relayerUrl: "/api/relayer/11155111",
    },
    [MainnetConfig.chainId]: {
      ...MainnetConfig,
      network: mainnetRpcUrl,
      relayerUrl: "/api/relayer/1",
    },
  },
});
```

Show chain selection explicitly in the UI. Do not silently reuse handles, credentials, or contract addresses across chains.

## Signer Selection

| Signer | Import | Purpose |
| --- | --- | --- |
| `WagmiSigner` | `@zama-fhe/react-sdk/wagmi` | React app using wagmi |
| `ViemSigner` | `@zama-fhe/sdk/viem` | viem wallet/public clients |
| `EthersSigner` | `@zama-fhe/sdk/ethers` | ethers v6 signer/provider |
| Custom `GenericSigner` | Project code | Smart wallet or custom transport |

The signer must provide chain id, account address, typed-data signatures, contract reads/writes, transaction receipt waiting, and block timestamp reads. If the signer can emit account/chain change events, implement `subscribe` so the SDK can reset state safely.

### Wagmi Adapter Fallback

`WagmiSigner` is preferred, but it depends on compatibility between the SDK and wagmi's internal action exports. When you hit a bundle-time export mismatch, implement a local `GenericSigner`:

```ts
import type { EIP712TypedData, GenericSigner } from "@zama-fhe/sdk";
import type { Config } from "wagmi";
import {
  getAccount,
  getBlock,
  getChainId,
  readContract,
  signTypedData,
  waitForTransactionReceipt,
  writeContract,
} from "wagmi/actions";

export function createWagmiGenericSigner(config: Config): GenericSigner {
  return {
    getChainId: () => Promise.resolve(getChainId(config)),
    async getAddress() {
      const account = getAccount(config);
      if (!account.address) throw new TypeError("Wallet not connected");
      return account.address;
    },
    signTypedData(typedData: EIP712TypedData) {
      const { EIP712Domain: _, ...types } = typedData.types;
      return signTypedData(config, {
        primaryType: Object.keys(types)[0]!,
        types,
        domain: typedData.domain,
        message: typedData.message,
      });
    },
    writeContract: (args) => writeContract(config, args as Parameters<typeof writeContract>[1]),
    readContract: (args) => readContract(config, args),
    waitForTransactionReceipt: (hash) => waitForTransactionReceipt(config, { hash }),
    async getBlockTimestamp() {
      return (await getBlock(config)).timestamp;
    },
  };
}
```

This fallback intentionally omits `subscribe`. If your wallet stack can reliably listen for disconnect, account change, and chain change events, add `subscribe(callbacks)` and call the corresponding callback from those events; otherwise manually call `sdk.revokeSession()` and refresh queries from wallet lifecycle events.

## Storage Selection

| Storage | Import | Purpose |
| --- | --- | --- |
| `indexedDBStorage` | `@zama-fhe/sdk` | Browser-persisted keypair/session/decrypt cache |
| `memoryStorage` | `@zama-fhe/sdk` | Scripts, tests, short-lived sessions |
| `chromeSessionStorage` | `@zama-fhe/sdk` | Chrome extension session storage |
| `asyncLocalStorage` | `@zama-fhe/sdk/node` | Node request-scoped storage |

Browser apps usually use `indexedDBStorage`. CLI tasks usually use `memoryStorage`. Multi-user servers need request isolation.

## FHE Artifact Cache

`RelayerWeb` and `RelayerNode` cache multi-MB FHE public keys and parameters.

| Runtime | Default Cache Behavior |
| --- | --- |
| `RelayerWeb` | IndexedDB, persisted across reloads |
| `RelayerNode` | In memory, lost after process restart |

The cache periodically revalidates the artifact source. Configure it with the following options:

```ts
const relayer = new RelayerWeb({
  getChainId: () => signer.getChainId(),
  fheArtifactStorage,
  fheArtifactCacheTTL,
  transports,
});
```

Use custom artifact storage only when the project explicitly needs a custom persistence or isolation strategy.

## Web Extension

A Chrome MV3 extension may need separate session storage because the service worker can be terminated at any time:

```ts
import {
  ZamaSDK,
  RelayerWeb,
  indexedDBStorage,
  chromeSessionStorage,
  SepoliaConfig,
} from "@zama-fhe/sdk";

const sdk = new ZamaSDK({
  relayer,
  signer,
  storage: indexedDBStorage,
  sessionStorage: chromeSessionStorage,
});
```

The extension manifest needs the `storage` permission.

## Registry Overrides

If a chain does not have an SDK default registry address, provide one explicitly:

```ts
const sdk = new ZamaSDK({
  relayer,
  signer,
  storage,
  registryAddresses: {
    [31337]: "0xRegistry",
  },
});
```

This affects confidential token wrapper discovery and registry helpers.

## SSR and Client Boundaries

Rules for frameworks such as Next.js:

- Components that use `@zama-fhe/react-sdk` must be client components.
- Do not import hooks or `ZamaProvider` in server components.
- Do not create `RelayerWeb` inside server-only modules.
- Avoid instantiating browser SDK code in modules shared by server and client code.
- Put provider wiring in a dedicated `"use client"` file.

If a page needs both server data and SDK interactions, split it into a server shell and a client child component.

## Lifecycle and Cleanup

Use:

```ts
await sdk.revokeSession();
sdk.dispose();
sdk.terminate();
```

- `revokeSession` clears the session signature and decrypt cache for the current requester.
- `dispose` removes signer lifecycle subscriptions.
- `terminate` also shuts down the relayer runtime worker or pool.

When a React `ZamaProvider` unmounts, it disposes the SDK instance it created. If the caller created and owns the relayer instance outside the provider, the caller must decide whether to terminate it separately.

## TTLs and Events

Configure decrypt keypair and session signature lifetimes deliberately. Source defaults are:

| Option | Default | Boundary |
| --- | --- | --- |
| `keypairTTL` | `2592000` seconds, 30 days | Must be greater than 0; values above 365 days are capped |
| `sessionTTL` | `2592000` seconds, 30 days | `0` means sign every time; core `ZamaSDKConfig` supports `"infinite"` |
| `registryTTL` | `86400` seconds, 24 hours | Affects registry lookup cache |

```ts
const sdk = new ZamaSDK({
  relayer,
  signer,
  storage,
  keypairTTL: 604800,
  sessionTTL: 3600,
  onEvent: ({ type, ...event }) => {
    console.debug(`[zama] ${type}`, event);
  },
});
```

Setting `sessionTTL: 0` disables session caching, so every operation that needs a session signature will trigger a wallet signature. Do this only when the product explicitly requires it.

Core `ZamaSDKConfig` supports `sessionTTL: "infinite"`, meaning the session signature does not actively expire. This fits controlled environments or extension/service scenarios, but the keypair is still constrained by `keypairTTL`. The currently published React `ZamaProviderProps` type is still `sessionTTL?: number`; before passing `"infinite"` directly to Provider props, check whether the local `node_modules/@zama-fhe/react-sdk/dist/index.d.ts` supports it.

If a numeric `sessionTTL` is greater than `keypairTTL`, the SDK clamps it to `keypairTTL` so `isAllowed()` does not remain true after the keypair has expired.

See `session-security.md` for more complete session/security details.
