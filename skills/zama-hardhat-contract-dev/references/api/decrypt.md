# Decrypt API

Hardhat plugin 提供两类 decrypt：

- `userDecrypt*`：检查 user 和 contract 是否有 ACL 权限。
- `publicDecrypt*`：检查 handle 是否 public decryptable。

mock/debug 还有 `fhevm.debugger.decrypt*`，它读取 mock 明文数据库，不适合证明 ACL 正确。

## FhevmType

```ts
import { FhevmType } from "@fhevm/hardhat-plugin";
```

常用值：

- `FhevmType.ebool`
- `FhevmType.euint8`
- `FhevmType.euint16`
- `FhevmType.euint32`
- `FhevmType.euint64`
- `FhevmType.euint128`
- `FhevmType.euint256`
- `FhevmType.eaddress`

`FhevmType.euint4` 存在于类型系统，但 encrypted input builder 当前没有对应 `add4`。

## user decrypt

```ts
const clear = await fhevm.userDecryptEuint(
  FhevmType.euint64,
  balanceHandle,
  vaultAddress,
  alice,
);
```

签名：

```ts
userDecryptEuint(type, handleBytes32, contractAddress, user, options?) => Promise<bigint>
userDecryptEbool(handleBytes32, contractAddress, user, options?) => Promise<boolean>
userDecryptEaddress(handleBytes32, contractAddress, user, options?) => Promise<string>
```

合约必须给 handle 设置：

```solidity
FHE.allowThis(value);
FHE.allow(value, user);
```

未授权测试：

```ts
let failed = false;
try {
  await fhevm.userDecryptEuint(FhevmType.euint64, balanceHandle, vaultAddress, bob);
} catch {
  failed = true;
}
expect(failed).to.eq(true);
```

## public decrypt

合约侧必须先：

```solidity
FHE.makePubliclyDecryptable(result);
```

测试侧：

```ts
const clear = await fhevm.publicDecryptEuint(FhevmType.euint64, handle);
```

签名：

```ts
publicDecryptEuint(type, handleBytes32, options?) => Promise<bigint>
publicDecryptEbool(handleBytes32, options?) => Promise<boolean>
publicDecryptEaddress(handleBytes32, options?) => Promise<string>
```

generic API：

```ts
const result = await fhevm.publicDecrypt([handle]);
const clear = result.clearValues[handle];
```

## generic user decrypt

多 handle、多合约或自定义 EIP-712 时使用：

```ts
const keypair = fhevm.generateKeypair();
const startTimestamp = Math.floor(Date.now() / 1000);
const durationDays = 1;
const eip712 = fhevm.createEIP712(
  keypair.publicKey,
  [vaultAddress],
  startTimestamp,
  durationDays,
);
const signature = await alice.signTypedData(eip712.domain, eip712.types, eip712.message);

const result = await fhevm.userDecrypt(
  [{ handle: balanceHandle, contractAddress: vaultAddress }],
  keypair.privateKey,
  keypair.publicKey,
  signature,
  [vaultAddress],
  alice.address,
  startTimestamp,
  durationDays,
);
```

简单测试优先用 `userDecryptEuint/Ebool/Eaddress`。

## debugger

```ts
const clear = await fhevm.debugger.decryptEuint(FhevmType.euint64, handle);
```

只用于 mock 环境下快速确认 FHE 运算或排查。它不证明用户 ACL 正确。
