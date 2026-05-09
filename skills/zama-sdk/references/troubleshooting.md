# Troubleshooting

This document lists common failure modes, likely causes, and the fastest order of checks.

## Import or Export Errors

Check import paths first:

- `RelayerNode` comes from `@zama-fhe/sdk/node`
- `RelayerCleartext` comes from `@zama-fhe/sdk/cleartext`
- `ViemSigner` comes from `@zama-fhe/sdk/viem`
- `EthersSigner` comes from `@zama-fhe/sdk/ethers`
- `WagmiSigner` comes from `@zama-fhe/react-sdk/wagmi`

Then check:

```bash
cat package.json
rg "@zama-fhe/(sdk|react-sdk)|RelayerWeb|RelayerNode|RelayerCleartext|ZamaProvider|WagmiSigner|ViemSigner|EthersSigner"
```

If pnpm install reports `No matching version found for @zama-fhe/react-sdk@...`, the version in the example or model memory is stale. Query real versions first, then synchronize both SDK packages:

```bash
pnpm view @zama-fhe/sdk versions --json
pnpm view @zama-fhe/react-sdk versions --json
```

If a production build reports `"watchConnection" is not exported by "wagmi/actions"` or a similar wagmi action export mismatch, the issue is incompatibility between the `@zama-fhe/react-sdk/wagmi` adapter and the current wagmi version. Do not modify `node_modules`; use the custom `GenericSigner` fallback in `configuration.md`, or pin to a verified SDK/wagmi/viem version combination.

## `window is not defined` or SSR Crash

Likely causes:

- A server component imports a React SDK hook.
- `RelayerWeb` is created in server-side module scope.
- The provider file is missing `"use client"`.
- A client/server shared module instantiates browser SDK code.

Fixes:

- Move the provider and SDK browser runtime into a client component.
- Separate server-only API route code from browser code.
- Dynamically import client-only components when necessary.

## Worker, WASM, or SharedArrayBuffer Issues

Symptoms:

- Encryption is stuck during initialization.
- Browser console mentions worker or WASM loading.
- Browser console mentions COOP/COEP or SharedArrayBuffer.
- `relayer.status === "error"`.

Checks:

1. Inspect `relayer.initError`.
2. If available, add status logging with `onStatusChange`.
3. Configure headers:

```txt
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

4. If `threads` is configured, first set the thread count to 1 or remove `threads` to confirm whether the single-threaded fallback works.
5. If the application has CSP, confirm it allows `worker-src blob:`, `script-src 'wasm-unsafe-eval'`, and `connect-src https://cdn.zama.org`.
6. Confirm the bundler has not placed SDK runtime code into server code.

## Browser Credential Exposure

Danger sign:

```ts
auth: { __type: "ApiKeyHeader", value: "..." }
```

appears in browser code.

Fix browser config by using a proxy URL:

```ts
relayerUrl: "/api/relayer/11155111"
```

Keep private credentials only in server-side route handlers, workers, jobs, or secret managers.

## Encrypted Contract Call Reverts

Check:

- Whether the `contractAddress` used for encryption is the contract that calls `FHE.fromExternal`.
- Whether `userAddress` is the connected account.
- Whether the chain id matches the deployed contract and SDK transport.
- Whether ABI function name and argument order are correct.
- Whether handles and input proof come from the same encrypt call.
- Whether `Uint8Array` values are converted to hex only once.
- Whether the Solidity function accepts the encrypted external type plus proof.
- Whether the contract correctly propagates ACL after saving new handles.

## User Decryption Fails

Check in order:

1. Is the handle a zero handle? Zero handles should be displayed as 0 directly.
2. Does the handle belong to the supplied `contractAddress`?
3. Does the contract allow the current user or delegate?
4. Has the app called `sdk.allow` or `useAllow` for every required contract?
5. Has the session expired?
6. Did account or chain change?
7. Does the relayer proxy return 401, 403, or 5xx?
8. Is storage incorrectly shared across users?

## Unexpected Wallet Signature Prompts

Common cause: the decrypt query starts before cached authorization has been confirmed.

Fix:

```tsx
const { data: allowed } = useIsAllowed({
  contractAddresses: [contractAddress],
});

const decrypt = useUserDecrypt(
  { handles: [{ handle, contractAddress }] },
  { enabled: !!allowed },
);
```

Prefer an explicit "Authorize" action that calls `useAllow`.

## Public Decryption Fails

Public decrypt applies only to handles that contract logic has explicitly made public.

Check:

- Whether the contract requested or marked the value as public decryptable.
- Whether the handle comes from the correct contract and chain.
- Whether the app waited for the required off-chain proof flow.
- Whether the finalize ABI expects the submitted clear value encoding.
- Whether the callback has replay protection and requested/finalized guards.

## Token Balance Check Errors

Token operation balance checks may require decrypt credentials.

If balance check is unavailable:

- Call `token.allow()`, `sdk.allow([tokenAddress])`, or `useAllow`.
- Use `skipBalanceCheck` only when explicitly accepting on-chain revert risk.
- Refresh balance handles after account, chain, or token changes.

If balance is insufficient:

- Check token decimals.
- Check the connected account.
- Distinguish public ERC20 balance from confidential balance.
- Check wrapper and underlying token addresses.

If `NoCiphertextError` is thrown:

- It means the account has no encrypted balance handle; it is not equal to `0n`.
- UI should show an empty state or guide the user to shield.
- Do not classify it as a relayer failure.

## Registry or Wrapper Not Found

Check:

- Whether the current chain has a configured registry.
- Whether the local chain uses `registryAddresses`.
- Whether the token supports the expected ERC7984 interfaces.
- Whether the wrapper has the expected underlying public ERC20.
- Whether the signer's chain id matches the registry override chain id.

## Local Cleartext Mismatch

Cleartext mode applies only to compatible local cleartext deployments.

Failure signals:

- Using cleartext runtime on Sepolia or Mainnet.
- The local contract deployment's FHE mode does not match the cleartext runtime.
- The app expects public decrypt proof behavior that the cleartext setup does not support.
- Contract addresses were copied from a different local node session.

Fast checks:

```bash
cast client --rpc-url http://127.0.0.1:8545
cast chain-id --rpc-url http://127.0.0.1:8545
```

If forge-fhevm `deploy-local.sh` reports `could not detect a supported local RPC backend`, pass it explicitly:

```bash
LOCAL_STATE_RPC_NAMESPACE=anvil ./dependencies/forge-fhevm-<version>/deploy-local.sh --anvil-port 8545
```

## Security Checklist

- API keys are server-only.
- Mnemonics/private keys are not committed.
- Frontend config contains only public values.
- User decrypt authorization covers only necessary contracts.
- Session TTL is set deliberately.
- Clear decrypt cache on account or chain changes.
- Contract ACL matches UI decrypt assumptions.
- Public decrypt is used only for public data.
- Logs do not contain secrets, private keys, or sensitive signatures.
