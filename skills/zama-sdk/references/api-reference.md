# API Reference

本文件是安装包源码/类型入口索引。实际开发中应先安装 SDK，然后直接查看项目里的 `node_modules`，不依赖远程文档。

实测安装：

```bash
pnpm add @zama-fhe/sdk @zama-fhe/react-sdk
```

## 本地查看规则

先读安装后的 package exports：

```bash
sed -n '1,220p' node_modules/@zama-fhe/sdk/package.json
sed -n '1,220p' node_modules/@zama-fhe/react-sdk/package.json
```

再用 `rg` 直接查类型和实现：

```bash
rg -n "declare function useConfidentialTransfer|interface ConfidentialTransferParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts
rg -n "declare class ZamaSDK|declare class Token|interface ZamaSDKConfig" node_modules/@zama-fhe/sdk/dist/esm/*.d.ts
rg -n "declare class ViemSigner|writeConfidentialTransferContract" node_modules/@zama-fhe/sdk/dist/esm/viem/index.d.ts
```

包发布的是编译后的 `dist`，通常没有原始 `src/` 文件；但 `.d.ts` 文件里带有 `//#region src/...` 标记，可定位原源码模块名。查 API 时优先看 `.d.ts`，行为细节再看同目录 `.js` 或 `.js.map`。

## Package Paths

| Import path | 本地类型入口 | 什么时候看 |
| --- | --- | --- |
| `@zama-fhe/sdk` | `node_modules/@zama-fhe/sdk/dist/esm/index.d.ts` | `ZamaSDK`、`RelayerWeb`、`Token`、`ReadonlyToken`、storage、errors、events、contract builders、registry |
| `@zama-fhe/sdk/cleartext` | `node_modules/@zama-fhe/sdk/dist/esm/cleartext/index.d.ts` | 本地 cleartext runtime、`hardhatCleartextConfig`、`hoodiCleartextConfig` |
| `@zama-fhe/sdk/node` | `node_modules/@zama-fhe/sdk/dist/esm/node/index.d.ts` | Node 后端 runtime、worker pool、`asyncLocalStorage` |
| `@zama-fhe/sdk/query` | `node_modules/@zama-fhe/sdk/dist/esm/query/index.d.ts` | TanStack Query factories、query keys、mutation options、invalidation helpers |
| `@zama-fhe/sdk/viem` | `node_modules/@zama-fhe/sdk/dist/esm/viem/index.d.ts` | `ViemSigner` 和 viem read/write helper |
| `@zama-fhe/sdk/ethers` | `node_modules/@zama-fhe/sdk/dist/esm/ethers/index.d.ts` | `EthersSigner` 和 ethers read/write helper |
| `@zama-fhe/react-sdk` | `node_modules/@zama-fhe/react-sdk/dist/index.d.ts` | `ZamaProvider`、React hooks、hook 参数类型、re-exported SDK symbols |
| `@zama-fhe/react-sdk/wagmi` | `node_modules/@zama-fhe/react-sdk/dist/wagmi/index.d.ts` | `WagmiSigner` |

pnpm 会把 `node_modules/@zama-fhe/sdk` 做成 symlink，正常读这个稳定路径即可，不要依赖 `.pnpm/...` 的长路径。

## Core SDK API Map

| API | 什么时候使用 | 形式 | 本地查看 |
| --- | --- | --- | --- |
| `ZamaSDK` | 非 React 入口；组合 relayer、signer、storage、token registry 和 decrypt/session cache。 | `new ZamaSDK({ relayer, signer, storage })` | `rg -n "declare class ZamaSDK|interface ZamaSDKConfig" node_modules/@zama-fhe/sdk/dist/esm/*.d.ts` |
| `RelayerWeb` | Browser runtime；Web Worker/WASM encryption、user decrypt、public decrypt、proof request。 | `new RelayerWeb({ getChainId, transports, threads, security })` | `rg -n "declare class RelayerWeb|type RelayerWebConfig" node_modules/@zama-fhe/sdk/dist/esm/index.d.ts` |
| `RelayerNode` | Node.js backend、CLI、server-side relayer auth 和 worker pool。 | `new RelayerNode({ getChainId, transports, poolSize })` | `rg -n "declare class RelayerNode|interface RelayerNodeConfig" node_modules/@zama-fhe/sdk/dist/esm/node/index.d.ts` |
| `RelayerCleartext` | 本地 cleartext/dev 环境，不走真实 FHE 加密。 | `new RelayerCleartext(config)` | `rg -n "declare class RelayerCleartext|interface CleartextConfig" node_modules/@zama-fhe/sdk/dist/esm/cleartext/index.d.ts` |
| `Token` | ERC7984 confidential token 的 shield、transfer、unshield、approval、delegation。第一个参数是 confidential token address，不是 underlying public ERC20 address。 | `const token = sdk.createToken(confidentialTokenAddress, wrapperAddress); await token.shield(amount)` | `rg -n "declare class Token|interface ShieldOptions|interface UnshieldOptions" node_modules/@zama-fhe/sdk/dist/esm/*.d.ts` |
| `ReadonlyToken` | 只读 token metadata、encrypted handle、decrypted balance、batch balances。参数是 confidential token address。 | `const token = sdk.createReadonlyToken(confidentialTokenAddress); await token.balanceOf(owner)` | `rg -n "declare class ReadonlyToken|type BatchBalancesResult|interface BatchBalancesResult" node_modules/@zama-fhe/sdk/dist/esm/*.d.ts` |
| `WrappersRegistry` | registry discovery、public/confidential token 地址映射、分页 pairs。 | `sdk.registry.listPairs(...)` 或 `new WrappersRegistry({ signer })` | `rg -n "declare class WrappersRegistry|interface WrappersRegistryConfig|interface ListPairsOptions" node_modules/@zama-fhe/sdk/dist/esm/*.d.ts` |
| `ViemSigner` | viem wallet/public client 接入 SDK。 | `new ViemSigner({ walletClient, publicClient })` | `node_modules/@zama-fhe/sdk/dist/esm/viem/index.d.ts` |
| `EthersSigner` | ethers v6 provider/signer 或 injected `ethereum` 接入 SDK。 | `new EthersSigner({ ethereum })` / `new EthersSigner({ signer })` | `node_modules/@zama-fhe/sdk/dist/esm/ethers/index.d.ts` |
| `GenericSigner` | smart wallet、自定义 wallet transport 或测试替身。 | `class MySigner implements GenericSigner { ... }` | `rg -n "type GenericSigner|interface GenericSigner" node_modules/@zama-fhe/sdk/dist/esm/*.d.ts` |
| `GenericStorage` | 自定义持久化 keypair、session、decrypt cache。 | `{ get, set, delete } satisfies GenericStorage` | `rg -n "type GenericStorage|declare class MemoryStorage|IndexedDBStorage|ChromeSessionStorage" node_modules/@zama-fhe/sdk/dist/esm/index.d.ts` |
| `asyncLocalStorage` | Node 多请求隔离 storage。 | `storage: asyncLocalStorage` | `rg -n "asyncLocalStorage|AsyncLocalMapStorage" node_modules/@zama-fhe/sdk/dist/esm/node/index.d.ts` |
| contract builders | 需要低层 read/write config 或 viem/ethers helper，而不是 `Token` abstraction。 | `wrapContract(...)`、`writeWrapContract(...)`、`readConfidentialBalanceOfContract(...)` | `rg -n "Contract\\(|write.*Contract|read.*Contract" node_modules/@zama-fhe/sdk/dist/esm/index.d.ts node_modules/@zama-fhe/sdk/dist/esm/viem/index.d.ts node_modules/@zama-fhe/sdk/dist/esm/ethers/index.d.ts` |
| errors | 捕获 typed SDK errors，生成 UI/CLI 可恢复提示。 | `error instanceof SigningRejectedError` | `rg -n "Error|ZamaError|ZamaErrorCode" node_modules/@zama-fhe/sdk/dist/esm/index.d.ts` |
| event decoders | 从 logs 解析 wrap、unwrap、delegation、activity feed 和 encrypted handles。 | `findWrapped(logs)`、`parseActivityFeed(logs)`、`extractEncryptedHandles(logs)` | `rg -n "decode|find|parseActivityFeed|extractEncryptedHandles|ACL_TOPICS|TOKEN_TOPICS" node_modules/@zama-fhe/sdk/dist/esm/index.d.ts` |

## React API Map

所有 React hooks 都在 `node_modules/@zama-fhe/react-sdk/dist/index.d.ts`。使用前先确认组件在 `ZamaProvider` 和 TanStack Query provider 下面。

| API | 什么时候使用 | 形式 | 本地查看 |
| --- | --- | --- | --- |
| `ZamaProvider` | React app 中连接 relayer、signer、storage 和 SDK context。 | `<ZamaProvider relayer={relayer} signer={signer} storage={indexedDBStorage}>...</ZamaProvider>` | `rg -n "interface ZamaProviderProps|declare function ZamaProvider" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useZamaSDK` | 组件中直接访问底层 `ZamaSDK`。 | `const sdk = useZamaSDK()` | `rg -n "declare function useZamaSDK" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useEncrypt` | 自定义 FHE 合约调用前生成 encrypted handles 和 input proof。 | `useEncrypt().mutateAsync({ values, contractAddress, userAddress })` | `rg -n "useEncrypt|EncryptParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useUserDecrypt` | 解密已由 ACL/session 授权的 arbitrary handles。 | `useUserDecrypt({ handles }, { enabled })` | `rg -n "useUserDecrypt|UserDecryptQueryConfig|DecryptHandle" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `usePublicDecrypt` | public encrypted handles 解密，无需用户 credential。 | `usePublicDecrypt().mutateAsync(handles)` | `rg -n "usePublicDecrypt|PublicDecryptResult" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useGenerateKeypair` | 手动生成 decrypt keypair。 | `useGenerateKeypair().mutateAsync()` | `rg -n "useGenerateKeypair|KeypairType" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useCreateEIP712` | 手动创建 user decrypt 授权签名的 typed data。 | `useCreateEIP712().mutateAsync(params)` | `rg -n "useCreateEIP712|CreateEIP712Params" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useCreateDelegatedUserDecryptEIP712` | 手动创建 delegated decrypt 授权 typed data。 | `useCreateDelegatedUserDecryptEIP712().mutateAsync(params)` | `rg -n "useCreateDelegatedUserDecryptEIP712|CreateDelegatedUserDecryptEIP712Params" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useDelegatedUserDecrypt` | 使用 delegation credentials 解密 handles。 | `useDelegatedUserDecrypt().mutateAsync(params)` | `rg -n "useDelegatedUserDecrypt|DelegatedUserDecryptParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useRequestZKProofVerification` | 提交 ZK proof 并获得 input proof bytes。 | `useRequestZKProofVerification().mutateAsync(zkProof)` | `rg -n "useRequestZKProofVerification|ZKProofLike" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `usePublicKey` / `usePublicParams` | 读取 relayer FHE public key / params。 | `usePublicKey()`、`usePublicParams(bits)` | `rg -n "usePublicKey|usePublicParams|PublicKeyData|PublicParamsData" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useAllow` / `useIsAllowed` / `useRevoke` / `useRevokeSession` | 管理 user decrypt session 授权。 | `useAllow().mutateAsync(addresses)`、`useIsAllowed({ contractAddresses })` | `rg -n "useAllow|useIsAllowed|useRevoke|useRevokeSession" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useToken` / `useReadonlyToken` | React 中创建 token abstraction。 | `useToken({ tokenAddress, wrapperAddress })`、`useReadonlyToken(address)` | `rg -n "useToken\\(|useReadonlyToken|UseZamaConfig" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useConfidentialBalance` / `useConfidentialBalances` | 解密展示单个或多个 confidential balances。 | `useConfidentialBalance({ tokenAddress, owner })` | `rg -n "useConfidentialBalance|useConfidentialBalances|UseConfidentialBalance" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useShield` | 把公开 ERC20 wrap/shield 成 confidential token。 | `useShield({ tokenAddress, wrapperAddress }).mutateAsync({ amount, approvalStrategy })` | `rg -n "useShield|ShieldParams|UseShieldConfig" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useApproveUnderlying` | 对 wrapper 执行 underlying ERC20 approval。 | `useApproveUnderlying({ tokenAddress, wrapperAddress }).mutateAsync({ amount })` | `rg -n "useApproveUnderlying|ApproveUnderlyingParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useUnderlyingAllowance` | 检查当前 signer 给 wrapper 的 underlying ERC20 allowance。 | `useUnderlyingAllowance({ tokenAddress, wrapperAddress })` | `rg -n "useUnderlyingAllowance|UseUnderlyingAllowanceConfig" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useConfidentialTransfer` | 用户发送 encrypted token amount。 | `useConfidentialTransfer({ tokenAddress }).mutateAsync({ to, amount })` | `rg -n "useConfidentialTransfer|ConfidentialTransferParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useConfidentialTransferFrom` | operator 代表 owner 执行 confidential transfer。 | `useConfidentialTransferFrom({ tokenAddress }).mutateAsync({ from, to, amount })` | `rg -n "useConfidentialTransferFrom|ConfidentialTransferFromParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useConfidentialApprove` / `useConfidentialIsApproved` | confidential operator approval 和状态检查。 | `useConfidentialApprove({ tokenAddress }).mutateAsync({ spender, until })` | `rg -n "useConfidentialApprove|useConfidentialIsApproved|ConfidentialApproveParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useUnwrap` / `useUnwrapAll` / `useFinalizeUnwrap` | 自定义两阶段 unwrap/unshield 流程。 | `useUnwrap({ tokenAddress, wrapperAddress }).mutateAsync({ amount })`、`useFinalizeUnwrap({ tokenAddress, wrapperAddress }).mutateAsync({ burnAmountHandle })` | `rg -n "useUnwrap|useUnwrapAll|useFinalizeUnwrap|UnwrapParams|FinalizeUnwrapParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useUnshield` / `useUnshieldAll` / `useResumeUnshield` | 高层 unshield 流程和中断恢复。 | `useUnshield({ tokenAddress, wrapperAddress }).mutateAsync({ amount })` | `rg -n "useUnshield|useUnshieldAll|useResumeUnshield|UnshieldParams|ResumeUnshieldParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useDelegateDecryption` / `useRevokeDelegation` / `useDelegationStatus` | delegated decryption 授权、撤销和状态展示。 | `useDelegateDecryption({ tokenAddress }).mutateAsync({ delegateAddress, expirationDate })` | `rg -n "useDelegateDecryption|useRevokeDelegation|useDelegationStatus|DelegateDecryptionParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| `useDecryptBalanceAs` / `useBatchDecryptBalancesAs` | delegate 代用户解密一个或多个 balances。 | `useDecryptBalanceAs(tokenAddress).mutateAsync(params)` | `rg -n "useDecryptBalanceAs|useBatchDecryptBalancesAs|DecryptBalanceAsParams" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| registry hooks | token/wrapper discovery、pairs、registry address、validity。 | `useListPairs(...)`、`useConfidentialTokenAddress(...)`、`useTokenAddress(...)` | `rg -n "useListPairs|useWrapperDiscovery|useWrappersRegistryAddress|useTokenPairs|useConfidentialTokenAddress|useTokenAddress|useIsConfidentialTokenValid" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| metadata/status hooks | token metadata、activity feed、interface checks、total supply。 | `useMetadata(tokenAddress)`、`useActivityFeed(config)`、`useIsConfidential(address)` | `rg -n "useMetadata|useActivityFeed|useIsConfidential|useIsWrapper|useTotalSupply" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |
| suspense variants | React Suspense UI 中使用。 | `useMetadataSuspense(...)`、`useWrapperDiscoverySuspense(...)` | `rg -n "Suspense" node_modules/@zama-fhe/react-sdk/dist/index.d.ts` |

## Query Factory API

如果项目不是 React，但仍使用 TanStack Query，读 `@zama-fhe/sdk/query`：

```bash
rg -n "QueryOptions|MutationOptions|zamaQueryKeys|invalidateAfter" node_modules/@zama-fhe/sdk/dist/esm/query/index.d.ts
```

常见用途：

| 任务 | 查看 |
| --- | --- |
| 自定义 query hooks | `confidentialBalanceQueryOptions`、`confidentialBalancesQueryOptions`、`activityFeedQueryOptions` |
| 自定义 mutation hooks | `shieldMutationOptions`、`confidentialTransferMutationOptions`、`unshieldMutationOptions` |
| session/decrypt hooks | `allowMutationOptions`、`isAllowedQueryOptions`、`userDecryptQueryOptions`、`publicDecryptMutationOptions` |
| registry queries | `listPairsQueryOptions`、`tokenAddressQueryOptions`、`confidentialTokenAddressQueryOptions` |
| cache keys | `zamaQueryKeys`、`hashFn` |
| manual invalidation | `invalidateAfterShield`、`invalidateAfterTransfer`、`invalidateAfterUnshield`、`invalidateWalletLifecycleQueries` |

## 选择指南

| 任务 | 首选入口 |
| --- | --- |
| React token dashboard | `@zama-fhe/react-sdk/dist/index.d.ts` 中的 `ZamaProvider`、`useConfidentialBalance`、`useMetadata`、`useActivityFeed` |
| React token actions | `useShield`、`useConfidentialTransfer`、`useUnshield`、`useResumeUnshield` |
| Operator / delegated flows | `useConfidentialApprove`、`useConfidentialTransferFrom`、`useDelegateDecryption`、`useDecryptBalanceAs` |
| 自定义 encrypted 合约 | `useEncrypt`、contract write、`useIsAllowed`、`useUserDecrypt` |
| Vanilla TS / backend | `@zama-fhe/sdk` 的 `ZamaSDK`、`RelayerWeb` 或 `@zama-fhe/sdk/node` 的 `RelayerNode` |
| Registry discovery | `WrappersRegistry` 或 registry hooks |
| Local/dev cleartext | `@zama-fhe/sdk/cleartext` |
| Cache/query plumbing | `@zama-fhe/sdk/query` |
