# 自定义合约

本文件适用于非 token 的 FHEVM 合约，例如 vault、auction、voting、private counter、matching engine，以及应用自定义 encrypted state。

这类场景称为低层 **Encrypt & decrypt**：token hooks 会自动处理 encrypted token flow，但自定义合约需要显式使用 `useEncrypt`、合约写入和 `useUserDecrypt`。

## 端到端流程

1. 读取当前 signer address 和 chain id。
2. 用将要消费 input 的合约地址加密明文值。
3. 把 encrypted handles 和 input proof 转为 hex。
4. 调用接收 encrypted external input 和 `bytes proof` 的 Solidity 函数。
5. 如果 UI 需要展示结果，从合约读回 encrypted handle。
6. 确认 ACL 允许用户或 delegate 解密该 handle。
7. 私有值使用 `sdk.userDecrypt`，公开 reveal 流程使用 `sdk.publicDecrypt`。

## 要匹配的 Solidity 形态

典型 Solidity 函数：

```solidity
function submit(externalEuint64 amount, bytes calldata inputProof) external {
    euint64 value = FHE.fromExternal(amount, inputProof);
    _balances[msg.sender] = FHE.add(_balances[msg.sender], value);
    FHE.allowThis(_balances[msg.sender]);
    FHE.allow(_balances[msg.sender], msg.sender);
}
```

SDK 加密时的 `contractAddress` 必须是这个调用 `FHE.fromExternal` 的合约地址。

## 加密输入

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

支持的 value shape：

| FHE type | JS value |
| --- | --- |
| `ebool` | `boolean` 或 `bigint` 0/1 |
| `euint8` | `bigint` |
| `euint16` | `bigint` |
| `euint32` | `bigint` |
| `euint64` | `bigint` |
| `euint128` | `bigint` |
| `euint256` | `bigint` |
| `eaddress` | `0x...` address |

如果加密结果里 handles 为空，先检查 `contractAddress` 和 `userAddress` 是否是有效地址，并确认钱包已连接后再调用 encrypt。

## 写合约

```ts
const txHash = await sdk.signer.writeContract({
  address: contractAddress,
  abi,
  functionName: "submit",
  args: [encryptedAmount, inputProof],
});

await sdk.signer.waitForTransactionReceipt(txHash);
```

同一次 `encrypt` 产生的 handles 和 input proof 必须一起使用。不要混用不同 encrypt 调用的 handles 和 proof。

## 读取 Handles

交易完成后，从合约读取暴露的 handle：

```ts
const handle = (await sdk.signer.readContract({
  address: contractAddress,
  abi,
  functionName: "balanceOf",
  args: [userAddress],
})) as `0x${string}`;
```

如果 handle 已经是 `0x...` 字符串，直接保存。只有 `Uint8Array` 才需要 `bytesToHex`。

## 用户解密

私有 decrypt 需要合约侧 ACL 和钱包 credentials：

```ts
await sdk.allow([contractAddress]);

const result = await sdk.userDecrypt([
  { handle, contractAddress },
]);

const clearBalance = result[handle] as bigint;
```

规则：

- 每个 handle 都必须包含拥有它的 `contractAddress`
- `contractAddress` 是拥有 encrypted handle 的合约，不一定是当前发起调用的合约
- zero handle 可以直接显示为 0，不需要请求 relayer
- credentials 按 requester、chain、contracts 和 TTL cache
- account 或 chain 变化后需要重新授权

React query 模式：

```tsx
const { mutate: allow, isPending: isAllowing } = useAllow();
const { data: isAllowed } = useIsAllowed({ contractAddresses: [contractAddress] });

const { data, isPending } = useUserDecrypt(
  { handles: [{ handle, contractAddress }] },
  { enabled: !!isAllowed },
);
```

当 `isAllowed` 为 false 时，提供显式 authorize 按钮。这样可以避免 decrypt query 在页面渲染时触发钱包弹窗。

## 一次预授权

常用 app 模式是只在 authorization 已 cache 后渲染 children：

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
      {isPending ? "签名中..." : "授权解密"}
    </button>
  );
}
```

授权完成后，嵌套的 `useUserDecrypt` 或 `useConfidentialBalance` 可以复用 cached credentials。

## 多合约 Handles

`useUserDecrypt` 和 `sdk.userDecrypt` 可以处理来自多个合约的值。SDK 会按 contract address 分组，并对每组发起一次 decrypt 请求：

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

返回数据按 handle 作为 key。

上例中的 `allowed` 应来自 `useIsAllowed({ contractAddresses: [tokenA, tokenB] })` 或等价的授权 gate。React SDK 的 `useUserDecrypt` 默认要求调用方显式传 `enabled`，避免页面渲染时直接触发钱包签名。

## 持久化 Cache

Decrypted values 会被 cache，并按 signer 和 contract 维度隔离。取决于 storage，cache 可以跨页面 reload 保留。revoke flows、钱包断开、account 变化、chain 变化或显式 cache clearing 会清理 cache。

## 公开解密

public decrypt 只用于合约明确允许公开的值。Solidity 侧通常需要对目标 encrypted value 调用公开解密授权，例如 `FHE.makePubliclyDecryptable(value)`，再由 off-chain relayer/KMS 返回 clear value 和 proof。`allowForDecryption` 是 ACL 合约的底层接口；业务合约中不要写成 `FHE.allowForDecryption(...)`。

```ts
const {
  clearValues,
  abiEncodedClearValues,
  decryptionProof,
} = await sdk.publicDecrypt([handle]);
```

`decryptionProof` 和 `abiEncodedClearValues` 通常传给链上 finalize callback，由合约验证签名。必须精确匹配 callback ABI；不要假设某个 ABI 生成的 proof 能用于另一个 ABI。

如果只是让当前用户读取自己的值，不要用 public decrypt；应使用 `sdk.userDecrypt([{ handle, contractAddress }])`，并在合约中通过 ACL 授权该用户。

## 委托解密

delegated decrypt 允许一个账户授权另一个账户解密特定 handles 或特定合约范围内的值。适合 dashboard、service agent、custodial view 或 delegated portfolio read。

高层入口包括：

- `sdk.delegatedCredentials`
- `relayer.createDelegatedUserDecryptEIP712`
- `relayer.delegatedUserDecrypt`
- React delegation hooks

delegation 不是 ERC20 allowance。它有独立的 delegator、delegate、contract、handle、expiry 和 revocation 模型。

## 事件和 Activity Decoding

SDK 导出 token 与 registry flow 的 event/activity helper。自定义合约优先使用 viem/ethers 的常规 ABI decoding；只有 event format 属于 SDK token 或 activity abstraction 时再使用 SDK decoders。

## 常见合约接入错误

- 用 proxy/router address 加密，但 `FHE.fromExternal` 实际在另一个合约执行
- decrypt 时把某个合约的 handle 与另一个 `contractAddress` 搭配
- 写入新 handle 后忘记 `FHE.allowThis`
- 用户需要解密的值忘记 `FHE.allow(handle, user)`
- 对已经是 `0x...` 的 handle 再次 `bytesToHex`
- 对用户私有值使用 `publicDecrypt`
- 用户尚未连接或授权时自动触发 `userDecrypt`
