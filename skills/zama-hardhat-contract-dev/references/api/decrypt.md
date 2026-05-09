# Decrypt API

The Hardhat plugin provides two decrypt flows:

- `userDecrypt*`: checks whether the user and contract have ACL permissions.
- `publicDecrypt*`: checks whether the handle is publicly decryptable.

Mock/debug mode also exposes `fhevm.debugger.decrypt*`, which reads the mock plaintext database. It is useful for troubleshooting, but it does not prove that ACLs are correct.

## FhevmType

```ts
import { FhevmType } from "@fhevm/hardhat-plugin";
```

Common values:

- `FhevmType.ebool`
- `FhevmType.euint8`
- `FhevmType.euint16`
- `FhevmType.euint32`
- `FhevmType.euint64`
- `FhevmType.euint128`
- `FhevmType.euint256`
- `FhevmType.eaddress`

`FhevmType.euint4` exists in the type system, but the encrypted input builder currently has no corresponding `add4`.

## user decrypt

```ts
const clear = await fhevm.userDecryptEuint(
  FhevmType.euint64,
  balanceHandle,
  vaultAddress,
  alice,
);
```

Signatures:

```ts
userDecryptEuint(type, handleBytes32, contractAddress, user, options?) => Promise<bigint>
userDecryptEbool(handleBytes32, contractAddress, user, options?) => Promise<boolean>
userDecryptEaddress(handleBytes32, contractAddress, user, options?) => Promise<string>
```

The contract must grant permissions on the handle:

```solidity
FHE.allowThis(value);
FHE.allow(value, user);
```

Unauthorized-user test:

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

The contract must first call:

```solidity
FHE.makePubliclyDecryptable(result);
```

Test side:

```ts
const clear = await fhevm.publicDecryptEuint(FhevmType.euint64, handle);
```

Signatures:

```ts
publicDecryptEuint(type, handleBytes32, options?) => Promise<bigint>
publicDecryptEbool(handleBytes32, options?) => Promise<boolean>
publicDecryptEaddress(handleBytes32, options?) => Promise<string>
```

Generic API:

```ts
const result = await fhevm.publicDecrypt([handle]);
const clear = result.clearValues[handle];
```

## generic user decrypt

Use this for multiple handles, multiple contracts, or custom EIP-712 flows:

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

For simple tests, prefer `userDecryptEuint/Ebool/Eaddress`.

## debugger

```ts
const clear = await fhevm.debugger.decryptEuint(FhevmType.euint64, handle);
```

Use this only in mock environments for quick FHE arithmetic checks or debugging. It does not prove that user ACLs are correct.
