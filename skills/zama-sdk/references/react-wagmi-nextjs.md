# React, Wagmi, and Next.js

This document applies to React frontends, Next.js app router projects, wagmi wallet integration, and SDK hook composition. The official React SDK hooks are based on TanStack Query and provide automatic cache invalidation and cached decryption where appropriate.

## React Reference Map

| Page | Purpose |
| --- | --- |
| `ZamaProvider` | Required context provider that connects relayer, signer, and storage |
| `useConfidentialBalance` | Decrypt and display token balances |
| `useShield` | Convert public ERC20 into confidential form |
| `useConfidentialTransfer` | Send an encrypted token amount |
| `useUnshield` | Convert confidential tokens back to public ERC20 |
| Query keys | Manual invalidation and custom query composition |

## Provider Stack

`ZamaProvider` must be nested under `QueryClientProvider`. Example for a wagmi project:

```tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  ZamaProvider,
  RelayerWeb,
  SepoliaConfig,
  indexedDBStorage,
} from "@zama-fhe/react-sdk";
import { WagmiSigner } from "@zama-fhe/react-sdk/wagmi";
import { WagmiProvider } from "wagmi";

const queryClient = new QueryClient();
const signer = new WagmiSigner({ config: wagmiConfig });
const relayer = new RelayerWeb({
  getChainId: () => signer.getChainId(),
  transports: {
    [SepoliaConfig.chainId]: {
      ...SepoliaConfig,
      network: process.env.NEXT_PUBLIC_SEPOLIA_RPC_URL!,
      relayerUrl: "/api/relayer/11155111",
    },
  },
});

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={queryClient}>
        <ZamaProvider relayer={relayer} signer={signer} storage={indexedDBStorage}>
          {children}
        </ZamaProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}
```

For Vite + React + TypeScript, do not forget the React type packages and the Vite React plugin. A usable minimal dependency set:

```json
{
  "dependencies": {
    "@rainbow-me/rainbowkit": "^2.2.9",
    "@tanstack/react-query": "^5.90.7",
    "@zama-fhe/react-sdk": "^3.0.0",
    "@zama-fhe/sdk": "^3.0.0",
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
    "viem": "^2.38.5",
    "wagmi": "^2.18.1"
  },
  "devDependencies": {
    "@types/react": "^19.2.0",
    "@types/react-dom": "^19.2.0",
    "@vitejs/plugin-react": "^5.1.0",
    "typescript": "^5.9.0",
    "vite": "^7.2.0"
  }
}
```

Version numbers are a starting point, not permanent truth. For a new project, first query the current real versions with `pnpm view`; if you upgrade to a new wagmi/viem combination, run a production build because adapter compatibility issues often surface during bundling.

## Provider Props

| Prop | Meaning |
| --- | --- |
| `relayer` | `RelayerWeb`, `RelayerNode`, or `RelayerCleartext` |
| `signer` | `WagmiSigner`, `ViemSigner`, `EthersSigner`, or custom signer |
| `storage` | Keypair and decrypt cache storage |
| `sessionStorage` | Session signature storage |
| `keypairTTL` | Keypair TTL |
| `sessionTTL` | Session signature TTL |
| `registryAddresses` | Registry override per chain |
| `registryTTL` | Registry cache TTL |
| `onEvent` | Lifecycle event callback |

Use `useZamaSDK()` when a component needs direct access to the SDK:

```tsx
const sdk = useZamaSDK();
const address = await sdk.signer.getAddress();
```

## Custom Contract Hook Flow

```tsx
import {
  useAllow,
  useEncrypt,
  useIsAllowed,
  useUserDecrypt,
  useZamaSDK,
} from "@zama-fhe/react-sdk";
import { bytesToHex } from "viem";
import { useState } from "react";

const contractAddress = "0xYourContract" as const;

function ConfidentialAction() {
  const sdk = useZamaSDK();
  const encrypt = useEncrypt();
  const allow = useAllow();
  const { data: allowed } = useIsAllowed({
    contractAddresses: [contractAddress],
  });
  const [handles, setHandles] = useState<
    { handle: `0x${string}`; contractAddress: `0x${string}` }[]
  >([]);

  const decrypt = useUserDecrypt(
    { handles },
    { enabled: handles.length > 0 && !!allowed },
  );

  async function submit(amount: bigint) {
    if (!allowed) {
      await allow.mutateAsync([contractAddress]);
    }

    const userAddress = await sdk.signer.getAddress();

    const encrypted = await encrypt.mutateAsync({
      values: [{ type: "euint64", value: amount }],
      contractAddress,
      userAddress,
    });

    await sdk.signer.writeContract({
      address: contractAddress,
      abi,
      functionName: "submit",
      args: [bytesToHex(encrypted.handles[0]!), bytesToHex(encrypted.inputProof)],
    });

    const handle = (await sdk.signer.readContract({
      address: contractAddress,
      abi,
      functionName: "balanceOf",
      args: [userAddress],
    })) as `0x${string}`;

    setHandles([{ handle, contractAddress }]);
  }
}
```

## Authorization Gate

Do not trigger wallet signatures merely because a component rendered:

```tsx
const { data: allowed } = useIsAllowed({
  contractAddresses: [contractAddress],
});

const decrypt = useUserDecrypt(
  { handles: [{ handle, contractAddress }] },
  { enabled: !!allowed && !!handle },
);
```

Provide an explicit authorization action:

```tsx
const allow = useAllow();

async function authorize() {
  await allow.mutateAsync([contractAddress]);
}
```

## Hook Reference

Custom contract hooks:

| Hook | Purpose |
| --- | --- |
| `useZamaSDK` | Get the SDK from context |
| `useEncrypt` | Encrypt typed external input |
| `useAllow` | Create or refresh user decrypt authorization |
| `useIsAllowed` | Check cached authorization |
| `useUserDecrypt` | Decrypt authorized private handles |
| `usePublicDecrypt` | Request public decrypt for public handles |

Token hooks:

| Hook | Purpose |
| --- | --- |
| `useToken` | Read/write token abstraction |
| `useReadonlyToken` | Read-only token abstraction |
| `useConfidentialBalance` | Decrypt a single balance |
| `useConfidentialBalances` | Decrypt balances in batch |
| `useShield` | Convert public ERC20 to confidential token |
| `useConfidentialTransfer` | Encrypted transfer |
| `useConfidentialTransferFrom` | Operator transfer |
| `useConfidentialApprove` | Confidential operator approval |
| `useUnderlyingAllowance` | Check the underlying ERC20 allowance granted to the wrapper |
| `useApproveUnderlying` | Execute underlying ERC20 approval separately |
| `useUnshield` | Convert confidential token to public ERC20 |
| `useResumeUnshield` | Resume pending unshield |
| `useMetadata` | Read token name, symbol, and decimals |
| `useTotalSupply` | Read confidential token total supply |

The currently published types for `useConfidentialBalance` and `useConfidentialBalances` read the current signer's owner. To read an arbitrary owner, use `sdk.createReadonlyToken(tokenAddress).balanceOf(owner)`, or compose your own query from `@zama-fhe/sdk/query`.

Registry and discovery hooks:

| Hook | Purpose |
| --- | --- |
| `useWrappersRegistryAddress` | Registry for the current chain |
| `useListPairs` | Read public/confidential pairs with pagination |
| `useTokenPairsRegistry` / `useTokenPairsLength` / `useTokenPairsSlice` / `useTokenPair` | Low-level registry pair reads |
| `useConfidentialTokenAddress` | Public token to confidential token; parameter is `{ tokenAddress }`, returns `[found, confidentialTokenAddress]` |
| `useTokenAddress` | Confidential token to public token; parameter is `{ confidentialTokenAddress }`, returns `[found, tokenAddress]` |
| `useIsConfidentialTokenValid` | Validate that the confidential token returned by the registry is still valid |
| `useWrapperDiscovery` | Discover wrapper metadata |
| `useIsConfidential` / `useIsWrapper` | Interface detection |

Delegation hooks:

| Hook | Purpose |
| --- | --- |
| `useDelegateDecryption` | Authorize delegated decrypt |
| `useRevokeDelegation` | Revoke delegated decrypt |
| `useDelegationStatus` | Check delegation |
| `useDecryptBalanceAs` | Decrypt as a delegate |
| `useBatchDecryptBalancesAs` | Batch delegate decrypt |

## UI State Model

Do not collapse all state into one `loading` flag. Prefer splitting it into:

- `isConnecting`
- `isWrongChain`
- `isInitializingSDK`
- `isCheckingAuthorization`
- `isAuthorizing`
- `isEncrypting`
- `isWriting`
- `isConfirming`
- `isDecrypting`
- `isRefreshing`
- `lastError`

This gives users precise feedback and helps avoid unexpected signature prompts.

## Next.js Rules

- Put provider setup in a `"use client"` file.
- Server components can pass addresses, ABIs, and static metadata into client components.
- Client components handle wallet connection, SDK hooks, encrypted inputs, and decrypt.
- Relayer proxies and any private credentials go through server routes.
- Avoid importing SDK hooks in shared modules that server code will use.

## Browser Worker, WASM, and Headers

FHE encryption in the browser uses Web Workers and WASM.

If you explicitly configure `RelayerWeb({ threads })`, multi-threaded WASM needs `SharedArrayBuffer`, so the page must be cross-origin isolated:

```txt
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

Next.js:

```js
const nextConfig = {
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
          { key: "Cross-Origin-Embedder-Policy", value: "require-corp" },
        ],
      },
    ];
  },
};
```

Vite:

```ts
export default defineConfig({
  server: {
    headers: {
      "Cross-Origin-Opener-Policy": "same-origin",
      "Cross-Origin-Embedder-Policy": "require-corp",
    },
  },
});
```

Without these headers, the SDK attempts to fall back to the single-threaded path. The usual result is lower performance, not necessarily broken functionality.

If the application has a strict CSP, also allow workers and WASM:

```txt
Content-Security-Policy: worker-src blob:; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self' https://cdn.zama.org https://your-relayer-proxy.example;
```

## Error Handling Pattern

Start with a local error normalizer:

```ts
function getMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  return "Unknown Zama SDK error";
}
```

When the UI needs richer behavior, read `api-reference.md` and inspect `node_modules/@zama-fhe/react-sdk/dist/index.d.ts`, `node_modules/@zama-fhe/sdk/dist/esm/query/index.d.ts`, and the relevant SDK type entry points in the installed project.
