# Testing Public Decrypt

Use public decrypt only when the result is intended to be public.

Contract side:

```solidity
event ResultRequested(euint64 result);

euint64 private _result;

function requestResult() external {
    FHE.makePubliclyDecryptable(_result);
    emit ResultRequested(_result);
}

function result() external view returns (euint64) {
    return _result;
}
```

Test side:

```ts
await vault.requestResult();
const handle = await vault.result();
const clear = await fhevm.publicDecryptEuint(FhevmType.euint64, handle);
expect(clear).to.eq(100n);
```

## Unmarked Handles Should Fail

```ts
const handle = await vault.result();
let failed = false;
try {
  await fhevm.publicDecryptEuint(FhevmType.euint64, handle);
} catch {
  failed = true;
}
expect(failed).to.eq(true);
```

## Types

```ts
await fhevm.publicDecryptEbool(handle);
await fhevm.publicDecryptEuint(FhevmType.euint32, handle);
await fhevm.publicDecryptEaddress(handle);
```

Generic:

```ts
const result = await fhevm.publicDecrypt([handle0, handle1]);
const clear0 = result.clearValues[handle0];
```

## On-Chain Finalize

If the contract has `finalize(clear, proof)` and calls `FHE.checkSignatures`, the Hardhat plugin's high-level `publicDecryptEuint` returns only the clear value; it does not directly provide a Solidity callback proof. When testing this kind of flow:

- Prefer the project's existing Zama SDK or relayer runtime callback helper.
- Alternatively, in mock/debug mode, use `fhevm.debugger.createDecryptionSignatures(handles, clearValues)` to generate signature parameters.
- Cover wrong handle, wrong cleartext, duplicate finalize, and finalize without request.

Do not use a user decrypt signature as a public decrypt callback proof.
