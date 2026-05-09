# API Reference

This document is an index for installed package source/type entry points. In real development, install the SDK first and inspect the project's local `node_modules` instead of relying on remote documentation.

Tested install:

```bash
pnpm add @zama-fhe/sdk @zama-fhe/react-sdk
```

## Local Inspection Rules

First read the installed package exports:

```bash
sed -n '1,220p' node_modules/@zama-fhe/sdk/package.json
sed -n '1,220p' node_modules/@zama-fhe/react-sdk/package.json
```

Then use `rg` to search types and implementation directly:

```bash
rg -n "declare function useConfidentialTransfer|interface ConfidentialTransferParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts
rg -n "declare class ZamaSDK|declare class Token|interface ZamaSDKConfig" node_modules/@zama-fhe/sdk/dist/esm/*.d.ts
rg -n "declare class ViemSigner|writeConfidentialTransferContract" node_modules/@zama-fhe/sdk/dist/esm/viem/index.d.ts
```

Published packages contain compiled `dist` output and usually do not include original `src/` files; however, `.d.ts` files contain `//#region src/...` markers that identify the original source module. Prefer `.d.ts` files when checking APIs, then inspect sibling `.js` or `.js.map` files for behavior details.

## Version Audit Notes

The official GitBook documentation, sample projects, and API reports can briefly fall out of sync. When they conflict, trust the currently installed package's `package.json` exports, `dist/**/*.d.ts`, and `packages/*/src` source.

## Package Paths

| Import path | Local Type Entry | When to Inspect |
| --- | --- | --- |
| `@zama-fhe/sdk` | `node_modules/@zama-fhe/sdk/dist/esm/index.d.ts` | `ZamaSDK`, `RelayerWeb`, `Token`, `ReadonlyToken`, storage, errors, events, contract builders, registry |
| `@zama-fhe/sdk/cleartext` | `node_modules/@zama-fhe/sdk/dist/esm/cleartext/index.d.ts` | Local cleartext runtime, `hardhatCleartextConfig`, `hoodiCleartextConfig` |
| `@zama-fhe/sdk/node` | `node_modules/@zama-fhe/sdk/dist/esm/node/index.d.ts` | Node backend runtime, worker pool, `asyncLocalStorage` |
| `@zama-fhe/sdk/query` | `node_modules/@zama-fhe/sdk/dist/esm/query/index.d.ts` | TanStack Query factories, query keys, mutation options, invalidation helpers |
| `@zama-fhe/sdk/viem` | `node_modules/@zama-fhe/sdk/dist/esm/viem/index.d.ts` | `ViemSigner` and viem read/write helpers |
| `@zama-fhe/sdk/ethers` | `node_modules/@zama-fhe/sdk/dist/esm/ethers/index.d.ts` | `EthersSigner` and ethers read/write helpers |
| `@zama-fhe/react-sdk` | `node_modules/@zama-fhe/react-sdk/dist/index.d.ts` | `ZamaProvider`, React hooks, hook parameter types, re-exported SDK symbols |
| `@zama-fhe/react-sdk/wagmi` | `node_modules/@zama-fhe/react-sdk/dist/wagmi/index.d.ts` | `WagmiSigner` |

pnpm turns `node_modules/@zama-fhe/sdk` into a symlink. Read that stable path normally; do not depend on the long `.pnpm/...` path.

## Core SDK API Map

| API | When to Use | Shape | Local Inspection |
| --- | --- | --- | --- |
| `ZamaSDK` | Non-React entry point; composes relayer, signer, storage, token registry, and decrypt/session cache. | `new ZamaSDK({ relayer, signer, storage })` | `rg -n "declare class ZamaSDK|interface ZamaSDKConfig" node_modules/@zama-fhe/sdk/dist/esm/*.d.ts` |
| `RelayerWeb` | Browser runtime; Web Worker/WASM encryption, user decrypt, public decrypt, proof requests. | `new RelayerWeb({ getChainId, transports, threads, security })` | `rg -n "declare class RelayerWeb|type RelayerWebConfig" node_modules/@zama-fhe/sdk/dist/esm/index.d.ts` |
| `RelayerNode` | Node.js backend, CLI, server-side relayer auth, and worker pool. | `new RelayerNode({ getChainId, transports, poolSize })` | `rg -n "declare class RelayerNode|interface RelayerNodeConfig" node_modules/@zama-fhe/sdk/dist/esm/node/index.d.ts` |
| `RelayerCleartext` | Local cleartext/dev environment without real FHE encryption. | `new RelayerCleartext(config)` | `rg -n "declare class RelayerCleartext|interface CleartextConfig" node_modules/@zama-fhe/sdk/dist/esm/cleartext/index.d.ts` |
| `Token` | ERC7984 confidential token shield, transfer, unshield, approval, and delegation. The first argument is the confidential token address, not the underlying public ERC20 address. | `const token = sdk.createToken(confidentialTokenAddress, wrapperAddress); await token.shield(amount)` | `rg -n "declare class Token|interface ShieldOptions|interface UnshieldOptions" node_modules/@zama-fhe/sdk/dist/esm/*.d.ts` |
| `ReadonlyToken` | Read-only token metadata, encrypted handles, decrypted balances, and batch balances. Parameter is the confidential token address. | `const token = sdk.createReadonlyToken(confidentialTokenAddress); await token.balanceOf(owner)` | `rg -n "declare class ReadonlyToken|type BatchBalancesResult|interface BatchBalancesResult" node_modules/@zama-fhe/sdk/dist/esm/*.d.ts` |
| `WrappersRegistry` | Registry discovery, public/confidential token address mapping, and paginated pairs. | `sdk.registry.listPairs(...)` or `new WrappersRegistry({ signer })` | `rg -n "declare class WrappersRegistry|interface WrappersRegistryConfig|interface ListPairsOptions" node_modules/@zama-fhe/sdk/dist/esm/*.d.ts` |
| `ViemSigner` | Integrate viem wallet/public clients with the SDK. | `new ViemSigner({ walletClient, publicClient })` | `node_modules/@zama-fhe/sdk/dist/esm/viem/index.d.ts` |
| `EthersSigner` | Integrate ethers v6 provider/signer or injected `ethereum` with the SDK. | `new EthersSigner({ ethereum })` / `new EthersSigner({ signer })` | `node_modules/@zama-fhe/sdk/dist/esm/ethers/index.d.ts` |
| `GenericSigner` | Smart wallets, custom wallet transports, or test doubles. | `class MySigner implements GenericSigner { ... }` | `rg -n "type GenericSigner|interface GenericSigner" node_modules/@zama-fhe/sdk/dist/esm/*.d.ts` |
| `GenericStorage` | Custom persistence for keypairs, sessions, and decrypt cache. | `{ get, set, delete } satisfies GenericStorage` | `rg -n "type GenericStorage|declare class MemoryStorage|IndexedDBStorage|ChromeSessionStorage" node_modules/@zama-fhe/sdk/dist/esm/index.d.ts` |
| `asyncLocalStorage` | Node request-isolated storage. | `storage: asyncLocalStorage` | `rg -n "asyncLocalStorage|AsyncLocalMapStorage" node_modules/@zama-fhe/sdk/dist/esm/node/index.d.ts` |
| contract builders | Need low-level read/write config or viem/ethers helpers instead of the `Token` abstraction. | `wrapContract(...)`, `writeWrapContract(...)`, `readConfidentialBalanceOfContract(...)` | `rg -n "Contract\\(|write.*Contract|read.*Contract" node_modules/@zama-fhe/sdk/dist/esm/index.d.ts node_modules/@zama-fhe/sdk/dist/esm/viem/index.d.ts node_modules/@zama-fhe/sdk/dist/esm/ethers/index.d.ts` |
| errors | Catch typed SDK errors and produce recoverable UI/CLI messages. | `error instanceof SigningRejectedError` | `rg -n "Error|ZamaError|ZamaErrorCode" node_modules/@zama-fhe/sdk/dist/esm/index.d.ts` |
| event decoders | Parse wrap, unwrap, delegation, activity feed, and encrypted handles from logs. | `findWrapped(logs)`, `parseActivityFeed(logs)`, `extractEncryptedHandles(logs)` | `rg -n "decode|find|parseActivityFeed|extractEncryptedHandles|ACL_TOPICS|TOKEN_TOPICS" node_modules/@zama-fhe/sdk/dist/esm/index.d.ts` |

## React API Map

All React hooks are in `node_modules/@zama-fhe/react-sdk/dist/index.d.ts`. Before using them, confirm the component is under both `ZamaProvider` and the TanStack Query provider.

| API | When to Use | Shape | Local Inspection |
| --- | --- | --- | --- |
| `ZamaProvider` | Connect relayer, signer, storage, and SDK context in a React app. | `<ZamaProvider relayer={relayer} signer={signer} storage={indexedDBStorage}>...</ZamaProvider>` | `rg -n "interface ZamaProviderProps|declare function ZamaProvider" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useZamaSDK` | Directly access the underlying `ZamaSDK` from a component. | `const sdk = useZamaSDK()` | `rg -n "declare function useZamaSDK" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useEncrypt` | Generate encrypted handles and input proof before custom FHE contract calls. | `useEncrypt().mutateAsync({ values, contractAddress, userAddress })` | `rg -n "useEncrypt|EncryptParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useUserDecrypt` | Decrypt arbitrary handles authorized by ACL/session. | `useUserDecrypt({ handles }, { enabled })` | `rg -n "useUserDecrypt|UserDecryptQueryConfig|DecryptHandle" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `usePublicDecrypt` | Decrypt public encrypted handles without user credentials. | `usePublicDecrypt().mutateAsync(handles)` | `rg -n "usePublicDecrypt|PublicDecryptResult" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useGenerateKeypair` | Manually generate a decrypt keypair. | `useGenerateKeypair().mutateAsync()` | `rg -n "useGenerateKeypair|KeypairType" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useCreateEIP712` | Manually create typed data for a user decrypt authorization signature. | `useCreateEIP712().mutateAsync(params)` | `rg -n "useCreateEIP712|CreateEIP712Params" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useCreateDelegatedUserDecryptEIP712` | Manually create delegated decrypt authorization typed data. | `useCreateDelegatedUserDecryptEIP712().mutateAsync(params)` | `rg -n "useCreateDelegatedUserDecryptEIP712|CreateDelegatedUserDecryptEIP712Params" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useDelegatedUserDecrypt` | Decrypt handles using delegation credentials. | `useDelegatedUserDecrypt().mutateAsync(params)` | `rg -n "useDelegatedUserDecrypt|DelegatedUserDecryptParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useRequestZKProofVerification` | Submit a ZK proof and get input proof bytes. | `useRequestZKProofVerification().mutateAsync(zkProof)` | `rg -n "useRequestZKProofVerification|ZKProofLike" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `usePublicKey` / `usePublicParams` | Read relayer FHE public key / params. | `usePublicKey()`, `usePublicParams(bits)` | `rg -n "usePublicKey|usePublicParams|PublicKeyData|PublicParamsData" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useAllow` / `useIsAllowed` / `useRevoke` / `useRevokeSession` | Manage user decrypt session authorization. | `useAllow().mutateAsync(addresses)`, `useIsAllowed({ contractAddresses })` | `rg -n "useAllow|useIsAllowed|useRevoke|useRevokeSession" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useToken` / `useReadonlyToken` | Create token abstractions in React. | `useToken({ tokenAddress, wrapperAddress })`, `useReadonlyToken(address)` | `rg -n "useToken\\(|useReadonlyToken|UseZamaConfig" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useConfidentialBalance` / `useConfidentialBalances` | Decrypt and display one or multiple confidential balances for the current signer. Use core token or query factory for arbitrary owners. | `useConfidentialBalance({ tokenAddress })`, `useConfidentialBalances({ tokenAddresses })` | `rg -n "useConfidentialBalance|useConfidentialBalances|UseConfidentialBalance" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useShield` | Wrap/shield public ERC20 into confidential token. | `useShield({ tokenAddress, wrapperAddress }).mutateAsync({ amount, approvalStrategy })` | `rg -n "useShield|ShieldParams|UseShieldConfig" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useApproveUnderlying` | Execute underlying ERC20 approval for the wrapper. | `useApproveUnderlying({ tokenAddress, wrapperAddress }).mutateAsync({ amount })` | `rg -n "useApproveUnderlying|ApproveUnderlyingParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useUnderlyingAllowance` | Check the underlying ERC20 allowance granted by the current signer to the wrapper. | `useUnderlyingAllowance({ tokenAddress, wrapperAddress })` | `rg -n "useUnderlyingAllowance|UseUnderlyingAllowanceConfig" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useConfidentialTransfer` | User sends an encrypted token amount. | `useConfidentialTransfer({ tokenAddress }).mutateAsync({ to, amount })` | `rg -n "useConfidentialTransfer|ConfidentialTransferParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useConfidentialTransferFrom` | Operator executes confidential transfer on behalf of owner. | `useConfidentialTransferFrom({ tokenAddress }).mutateAsync({ from, to, amount })` | `rg -n "useConfidentialTransferFrom|ConfidentialTransferFromParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useConfidentialApprove` / `useConfidentialIsApproved` | Confidential operator approval and status check. | `useConfidentialApprove({ tokenAddress }).mutateAsync({ spender, until })` | `rg -n "useConfidentialApprove|useConfidentialIsApproved|ConfidentialApproveParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useUnwrap` / `useUnwrapAll` / `useFinalizeUnwrap` | Custom two-phase unwrap/unshield flow. | `useUnwrap({ tokenAddress, wrapperAddress }).mutateAsync({ amount })`, `useFinalizeUnwrap({ tokenAddress, wrapperAddress }).mutateAsync({ burnAmountHandle })` | `rg -n "useUnwrap|useUnwrapAll|useFinalizeUnwrap|UnwrapParams|FinalizeUnwrapParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useUnshield` / `useUnshieldAll` / `useResumeUnshield` | High-level unshield flow and interrupted-flow resume. | `useUnshield({ tokenAddress, wrapperAddress }).mutateAsync({ amount })` | `rg -n "useUnshield|useUnshieldAll|useResumeUnshield|UnshieldParams|ResumeUnshieldParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useDelegateDecryption` / `useRevokeDelegation` / `useDelegationStatus` | Delegated decryption authorization, revocation, and status display. | `useDelegateDecryption({ tokenAddress }).mutateAsync({ delegateAddress, expirationDate })` | `rg -n "useDelegateDecryption|useRevokeDelegation|useDelegationStatus|DelegateDecryptionParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useDecryptBalanceAs` / `useBatchDecryptBalancesAs` | Delegate decrypts one or multiple balances for a user. | `useDecryptBalanceAs(tokenAddress).mutateAsync(params)` | `rg -n "useDecryptBalanceAs|useBatchDecryptBalancesAs|DecryptBalanceAsParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| registry hooks | Token/wrapper discovery, pairs, registry address, validity. | `useConfidentialTokenAddress({ tokenAddress })`, `useTokenAddress({ confidentialTokenAddress })`, `useIsConfidentialTokenValid({ confidentialTokenAddress })` | `rg -n "useListPairs|useWrapperDiscovery|useWrappersRegistryAddress|useTokenPairs|useConfidentialTokenAddress|useTokenAddress|useIsConfidentialTokenValid" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| metadata/status hooks | Token metadata, activity feed, interface checks, total supply. | `useMetadata(tokenAddress)`, `useActivityFeed(config)`, `useIsConfidential(address)` | `rg -n "useMetadata|useActivityFeed|useIsConfidential|useIsWrapper|useTotalSupply" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| suspense variants | Use in React Suspense UI. | `useMetadataSuspense(...)`, `useWrapperDiscoverySuspense(...)` | `rg -n "Suspense" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |

## Query Factory API

If the project is not React but still uses TanStack Query, inspect `@zama-fhe/sdk/query`:

```bash
rg -n "QueryOptions|MutationOptions|zamaQueryKeys|invalidateAfter" node_modules/@zama-fhe/sdk/dist/esm/query/index.d.ts
```

Common uses:

| Task | Inspect |
| --- | --- |
| Custom query hooks | `confidentialBalanceQueryOptions`, `confidentialBalancesQueryOptions`, `activityFeedQueryOptions` |
| Custom mutation hooks | `shieldMutationOptions`, `confidentialTransferMutationOptions`, `unshieldMutationOptions` |
| Session/decrypt hooks | `allowMutationOptions`, `isAllowedQueryOptions`, `userDecryptQueryOptions`, `publicDecryptMutationOptions` |
| Registry queries | `listPairsQueryOptions`, `tokenAddressQueryOptions`, `confidentialTokenAddressQueryOptions` |
| Cache keys | `zamaQueryKeys`, `hashFn` |
| Manual invalidation | `invalidateAfterShield`, `invalidateAfterTransfer`, `invalidateAfterUnshield`, `invalidateWalletLifecycleQueries` |

## Selection Guide

| Task | Preferred Entry Point |
| --- | --- |
| React token dashboard | `ZamaProvider`, `useConfidentialBalance`, `useMetadata`, and `useActivityFeed` in `@zama-fhe/react-sdk/dist/index.d.ts` |
| React token actions | `useShield`, `useConfidentialTransfer`, `useUnshield`, `useResumeUnshield` |
| Operator / delegated flows | `useConfidentialApprove`, `useConfidentialTransferFrom`, `useDelegateDecryption`, `useDecryptBalanceAs` |
| Custom encrypted contract | `useEncrypt`, contract write, `useIsAllowed`, `useUserDecrypt` |
| Vanilla TS / backend | `ZamaSDK`, `RelayerWeb` from `@zama-fhe/sdk`, or `RelayerNode` from `@zama-fhe/sdk/node` |
| Registry discovery | `WrappersRegistry` or registry hooks |
| Local/dev cleartext | `@zama-fhe/sdk/cleartext` |
| Cache/query plumbing | `@zama-fhe/sdk/query` |
