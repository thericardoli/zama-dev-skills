# Node, Backend, and Local Development

This document applies to scripts, backend services, relayer proxy routes, server jobs, and local cleartext development.

The Node path uses `RelayerNode`, imported from the `@zama-fhe/sdk/node` subpath, and requires Node.js `>=22`. It uses native worker threads rather than browser Web Workers.

## Node SDK Factory

```ts
import { ZamaSDK, SepoliaConfig, memoryStorage } from "@zama-fhe/sdk";
import { RelayerNode } from "@zama-fhe/sdk/node";
import { ViemSigner } from "@zama-fhe/sdk/viem";

export function createZamaSdk({ walletClient, publicClient }: Clients) {
  const signer = new ViemSigner({ walletClient, publicClient });

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

  return new ZamaSDK({
    relayer,
    signer,
    storage: memoryStorage,
  });
}
```

This pattern is for trusted scripts and services. Keep private values in environment variables or a secret manager.

## Request-Scoped Storage

Multi-user servers should not share a single `memoryStorage` across unrelated users:

```ts
import { ZamaSDK } from "@zama-fhe/sdk";
import { asyncLocalStorage } from "@zama-fhe/sdk/node";

export async function withZamaRequest<T>(fn: (sdk: ZamaSDK) => Promise<T>) {
  return asyncLocalStorage.run(async () => {
    const sdk = new ZamaSDK({
      relayer,
      signer,
      storage: asyncLocalStorage,
    });

    return fn(sdk);
  });
}
```

Use request-scoped storage when decrypt credentials or caches depend on the current user.

In Express/Hono/Next routes, ensure SDK operations happen inside the `asyncLocalStorage.run()` callback; promises created outside the callback do not automatically inherit that request scope.

## Backend Proxy

Browser applications that need private relayer credentials should call a same-origin route:

```ts
export async function POST(request: Request) {
  const upstream = await fetch(process.env.ZAMA_RELAYER_URL!, {
    method: "POST",
    headers: {
      "content-type": request.headers.get("content-type") ?? "application/json",
      "x-api-key": process.env.RELAYER_API_KEY!,
    },
    body: await request.text(),
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: upstream.headers,
  });
}
```

Adjust path forwarding, CORS, streaming, and headers for the specific framework. The architectural rule is: the browser calls only `/api/relayer/<chain>`, and the server injects private credentials.

## Public Decryption Jobs

A common server job listens to contracts, requests public decrypt, then submits a finalize transaction:

```ts
const result = await sdk.publicDecrypt([handle]);

await sdk.signer.writeContract({
  address: contractAddress,
  abi,
  functionName: "finalizeReveal",
  args: [result.abiEncodedClearValues, result.decryptionProof],
});
```

Before submitting the callback, check:

- The contract actually requested public decrypt for that handle.
- The callback ABI matches the proof encoding.
- Replay and already-finalized states are handled.
- If the application is reorg-sensitive, wait for enough confirmations.

## Local Cleartext Runtime

```ts
import { ZamaSDK, memoryStorage } from "@zama-fhe/sdk";
import {
  RelayerCleartext,
  hardhatCleartextConfig,
  hoodiCleartextConfig,
} from "@zama-fhe/sdk/cleartext";

const relayer = new RelayerCleartext(hardhatCleartextConfig);
const sdk = new ZamaSDK({ relayer, signer, storage: memoryStorage });
```

Local Anvil/Hardhat needs the forge-fhevm cleartext host stack deployed first; otherwise the proof/handle produced by SDK encryption will not match the on-chain executor/ACL. Typical order:

```bash
# terminal 1
anvil --host 127.0.0.1 --port 8545 --chain-id 31337

# terminal 2
LOCAL_STATE_RPC_NAMESPACE=anvil ./dependencies/forge-fhevm-<version>/deploy-local.sh --anvil-port 8545
forge script script/DeployLocal.s.sol:DeployLocal --rpc-url http://127.0.0.1:8545 --broadcast --unlocked --sender 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266
```

The frontend `contractAddress` must come from the local deployment output for the same Anvil session; after restarting Anvil, redeploy and update the address file.

Cleartext mode is appropriate for:

- Local contract demos
- Deterministic integration tests
- Frontend development that should not wait for remote proofs
- Debugging app orchestration before connecting to a real FHE network

Do not use cleartext mode in production, Sepolia, or Mainnet paths.

The SDK source explicitly prevents cleartext mode from running on Ethereum Mainnet (`1`) and Sepolia (`11155111`). The Hoodi cleartext preset is a separate development/test configuration:

```ts
import { RelayerCleartext, hoodiCleartextConfig } from "@zama-fhe/sdk/cleartext";

const relayer = new RelayerCleartext(hoodiCleartextConfig);
```

A custom cleartext chain must provide a `CleartextConfig` whose `executorAddress`, `aclContractAddress`, and gateway verification contracts correspond to the locally deployed cleartext executor. For a forge-fhevm local stack, prefer `hardhatCleartextConfig` as the baseline and override only `chainId` and `network`.

## Worker and Lifecycle Management

The Node relayer runtime may hold worker threads or pools. Long-lived processes should shut down cleanly:

```ts
process.on("SIGTERM", () => {
  sdk.terminate();
  process.exit(0);
});
```

Short scripts:

```ts
try {
  await main();
} finally {
  sdk.terminate();
}
```

## CLI Script Pattern

```ts
async function main() {
  const sdk = createZamaSdk();
  const userAddress = await sdk.signer.getAddress();

  const encrypted = await sdk.relayer.encrypt({
    values: [{ type: "euint64", value: 10n }],
    contractAddress,
    userAddress,
  });

  // Write the contract, wait for the receipt, then decrypt if needed
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
```

Scripts should be as idempotent as possible. Before write transactions, print tx hashes, chain id, contract address, and signer address.

## Server-Side Security Checklist

- Do not commit private keys or mnemonics.
- Do not expose API keys to the browser bundle.
- Use per-request cache isolation for user decrypt flows.
- Call `terminate()` during worker shutdown.
- Explicitly check chain id and contract address before write transactions.
- Add replay protection to public decrypt callbacks.
- Do not log private keys, signed typed data, or decrypt secrets.
