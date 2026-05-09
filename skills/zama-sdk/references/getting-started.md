# Getting Started

Read this document first when integrating Zama SDK into a project. Understand what the SDK does, choose the packages and runtime environment, then use the minimal React, vanilla TypeScript, Node.js, or local development skeletons below.

## What the SDK Does

Zama SDK is the TypeScript application layer for confidential smart contracts. In a typical project, it is responsible for:

- Fetching public encryption material through the relayer runtime
- Encrypting external input before contract calls
- Generating encrypted handles and input proofs for Solidity `externalEuintX`, `externalEbool`, and `externalEaddress`
- Managing decrypt credentials authorized by wallet signatures
- Decrypting handles that the user is allowed to read through ACLs
- Requesting public decrypt results and proofs
- Wrapping ERC7984 confidential token shield, transfer, unshield, and balance flows into high-level APIs

The Solidity contract still defines the privacy policy. SDK code must match the contract ABI, target address, ACL design, and decrypt model.

## Official Feature Model

The official SDK documentation groups the main features into three categories:

| Feature | Meaning |
| --- | --- |
| Shield and unshield | Convert a public ERC20 token into an encrypted token, or convert it back to public ERC20 |
| Confidential transfer | Encrypt the transfer amount on the client, then submit the on-chain transaction |
| React hooks | TanStack Query-based hooks with cached decryption and automatic cache invalidation |

ERC7984 token projects should prefer the high-level token APIs and hooks. For non-token contracts, read `custom-contracts.md` and use the lower-level encrypt/decrypt flow.

## Two Packages

| Package | Use Case |
| --- | --- |
| `@zama-fhe/sdk` | Vanilla TypeScript, Node.js, CLI scripts, or non-React frameworks |
| `@zama-fhe/react-sdk` | React applications; includes providers/hooks and re-exports most core SDK symbols |

Signer adapters are still imported from subpaths, such as `@zama-fhe/sdk/viem`, `@zama-fhe/sdk/ethers`, and `@zama-fhe/react-sdk/wagmi`.

## Project Shapes

| Project Shape | Use |
| --- | --- |
| React / wagmi frontend | `@zama-fhe/react-sdk`, `ZamaProvider`, `WagmiSigner`, React hooks |
| Browser / vanilla TypeScript | `@zama-fhe/sdk`, `RelayerWeb`, `ZamaSDK`, `ViemSigner`, or a custom signer |
| Node script or backend | `@zama-fhe/sdk`, `@zama-fhe/sdk/node`, `RelayerNode` |
| Local cleartext app | `@zama-fhe/sdk/cleartext`, `RelayerCleartext` |
| ERC7984 confidential token UI | `Token`, `ReadonlyToken`, token hooks |
| Custom encrypted app | `relayer.encrypt`, contract writes, `sdk.userDecrypt`, `sdk.publicDecrypt` |

## Recommended Project Structure

React/wagmi application:

```text
src/
  app/
    providers.tsx          # WagmiProvider, QueryClientProvider, ZamaProvider
  lib/
    zama/
      config.ts            # chains, transport config, registry overrides
      sdk.ts               # relayer/signer helpers if needed
      contracts.ts         # addresses and ABI imports
      conversions.ts       # bytesToHex, handle guards, unit helpers
  features/
    confidential-token/
      hooks.ts             # compose token hooks for product UI
      components.tsx
    custom-contract/
      actions.ts           # encrypt + write + decrypt orchestration
```

Node backend:

```text
src/
  zama/
    config.ts              # chain ids, RPC URLs, private env reads
    signer.ts              # create ViemSigner or EthersSigner
    sdk.ts                 # ZamaSDK + RelayerNode factory
    proxy.ts               # optional browser-to-relayer proxy
    jobs.ts                # public decrypt or monitoring jobs
```

Keep contract ABI/address definitions separate from SDK creation logic. This makes chain switching, testing, and frontend/backend boundaries easier to audit.

## Installation

React / wagmi:

```bash
pnpm add @zama-fhe/react-sdk @zama-fhe/sdk @tanstack/react-query wagmi viem
```

Vanilla TypeScript or Node.js with viem:

```bash
pnpm add @zama-fhe/sdk viem
```

Vanilla TypeScript or Node.js with ethers:

```bash
pnpm add @zama-fhe/sdk ethers
```

Projects that run SDK code in Node should use Node.js `>=22`.

Do not copy stale version numbers into new projects. First query the real published versions, and keep `@zama-fhe/sdk` and `@zama-fhe/react-sdk` on the same release version:

```bash
pnpm view @zama-fhe/sdk version
pnpm view @zama-fhe/react-sdk version
```

React + TypeScript projects also need framework type packages such as `@types/react` and `@types/react-dom`. For wagmi projects, prefer `WagmiSigner` from `@zama-fhe/react-sdk/wagmi`; if the current SDK/wagmi combination fails to build, use the custom `GenericSigner` fallback in `configuration.md`.

## Authentication Rules

Relayer requests require an API key. Browser applications should forward relayer requests through a backend proxy so the key stays on the server:

```ts
relayerUrl: "https://your-app.com/api/relayer/11155111"
```

Server scripts and backend services can pass credentials directly in the transport config:

```ts
auth: { __type: "ApiKeyHeader", value: process.env.RELAYER_API_KEY! }
```

Expose only public variables in frontend frameworks. Next.js uses `NEXT_PUBLIC_`; Vite uses `VITE_`.

## Runtime Components

Every integration combines four parts:

| Part | Responsibility | Common Choices |
| --- | --- | --- |
| Relayer runtime | Encryption material, decrypt requests, proof requests | `RelayerWeb`, `RelayerNode`, `RelayerCleartext` |
| Signer | Chain id, account, typed-data signatures, contract calls | `WagmiSigner`, `ViemSigner`, `EthersSigner` |
| Storage | Keypair, session signature, decrypt cache | `indexedDBStorage`, `memoryStorage`, `asyncLocalStorage` |
| SDK facade | Credentials, cache, token registry, token objects | `ZamaSDK`, `ZamaProvider` |

## Minimal Browser SDK

```ts
import {
  ZamaSDK,
  RelayerWeb,
  SepoliaConfig,
  indexedDBStorage,
} from "@zama-fhe/sdk";
import { ViemSigner } from "@zama-fhe/sdk/viem";

const signer = new ViemSigner({ walletClient, publicClient });

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

export const sdk = new ZamaSDK({
  relayer,
  signer,
  storage: indexedDBStorage,
});
```

Browser code that needs relayer credentials should use a server-side proxy URL. Never put a private API key into the frontend bundle.

## First Confidential Transfer

The official 30-second flow is token-centric:

```ts
const token = sdk.createToken("0xYourEncryptedERC20");

await token.shield(1000n);
const balance = await token.balanceOf();
await token.confidentialTransfer("0xRecipient", 500n);
await token.unshield(500n);
```

ERC7984 confidential token applications should prefer this path. Only read `custom-contracts.md` when the contract itself defines custom encrypted parameters.

## Minimal React Provider

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
      network: "https://ethereum-sepolia-rpc.publicnode.com",
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

`ZamaProvider` must be nested under `QueryClientProvider`. In Next.js, this file must be client-only.

## Minimal React Token Page

```tsx
import { type FormEvent } from "react";
import { useAccount, useConnect, useDisconnect } from "wagmi";
import { injected } from "wagmi/connectors";
import {
  useConfidentialBalance,
  useConfidentialTransfer,
  useMetadata,
  useShield,
} from "@zama-fhe/react-sdk";

function MyTokenPage() {
  const tokenAddress = "0xYourEncryptedERC20" as const;
  const wrapperAddress = "0xYourWrapper" as const;
  const { address, isConnected } = useAccount();
  const { connect } = useConnect();
  const { disconnect } = useDisconnect();

  const { data: meta } = useMetadata(tokenAddress);
  const { data: balance, isLoading } = useConfidentialBalance({ tokenAddress });
  const shield = useShield({ tokenAddress, wrapperAddress });
  const transfer = useConfidentialTransfer({ tokenAddress });

  if (!isConnected) {
    return <button onClick={() => connect({ connector: injected() })}>Connect wallet</button>;
  }

  async function handleShield(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const amount = new FormData(e.currentTarget).get("amount") as string;
    await shield.mutateAsync({ amount: BigInt(amount) });
  }

  async function handleTransfer(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    await transfer.mutateAsync({
      to: data.get("to") as `0x${string}`,
      amount: BigInt(data.get("amount") as string),
    });
  }

  return (
    <section>
      <p>Connected: {address}</p>
      {meta && <p>{meta.name} ({meta.symbol})</p>}
      <p>Balance: {isLoading ? "Decrypting..." : balance?.toString()}</p>
      <form onSubmit={handleShield}>
        <input name="amount" type="number" required />
        <button disabled={shield.isPending}>Shield</button>
      </form>
      <form onSubmit={handleTransfer}>
        <input name="to" placeholder="0x..." required />
        <input name="amount" type="number" required />
        <button disabled={transfer.isPending}>Confidential transfer</button>
      </form>
      <button onClick={() => disconnect()}>Disconnect</button>
    </section>
  );
}
```

If the confidential token contract is itself the wrapper, `wrapperAddress` can be omitted. Most wrapped ERC20 projects have a separate wrapper address, so shield, unshield, underlying allowance, and approve underlying calls should pass it explicitly.

## Minimal Node SDK

```ts
import { ZamaSDK, SepoliaConfig, memoryStorage } from "@zama-fhe/sdk";
import { RelayerNode } from "@zama-fhe/sdk/node";
import { ViemSigner } from "@zama-fhe/sdk/viem";

const signer = new ViemSigner({ walletClient, publicClient });

export const sdk = new ZamaSDK({
  signer,
  storage: memoryStorage,
  relayer: new RelayerNode({
    getChainId: () => signer.getChainId(),
    transports: {
      [SepoliaConfig.chainId]: {
        ...SepoliaConfig,
        network: process.env.SEPOLIA_RPC_URL!,
        auth: { __type: "ApiKeyHeader", value: process.env.RELAYER_API_KEY! },
      },
    },
  }),
});
```

Long-lived servers should not share a single `memoryStorage` across users. Use request-scoped storage, or create SDK instances along trusted job boundaries.

## FHE Artifact Cache

`RelayerWeb` and `RelayerNode` cache large FHE public keys and parameters so they do not have to be downloaded on every startup. The browser runtime persists them in IndexedDB by default; the Node runtime stores them in memory by default. Adjust this with `fheArtifactStorage` and `fheArtifactCacheTTL`.

## Minimal Local Cleartext

```ts
import { ZamaSDK, memoryStorage } from "@zama-fhe/sdk";
import {
  RelayerCleartext,
  hardhatCleartextConfig,
} from "@zama-fhe/sdk/cleartext";

const relayer = new RelayerCleartext(hardhatCleartextConfig);
const sdk = new ZamaSDK({ relayer, signer, storage: memoryStorage });
```

Cleartext mode is only for development and testing against a compatible local stack. Do not use it for Sepolia or Mainnet paths.

## First Integration Checklist

- Decide whether this is a custom contract flow or an ERC7984 token flow.
- Confirm the chain id, contract address, user address, ABI, and network URL.
- The `contractAddress` used during encryption must be the contract that calls `FHE.fromExternal`.
- Convert `Uint8Array` handles and proofs to hex before contract writes.
- Handles read back from contracts are usually already `0x...` strings; keep them as-is.
- Gate user decryption behind wallet connection, correct chain, and authorization state.
- Keep private relayer credentials on the server only.
