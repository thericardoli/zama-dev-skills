# Testing Decrypt and ACL

After writing a new handle, the contract should set:

```solidity
FHE.allowThis(value);
FHE.allow(value, user);
```

`allowThis` lets the contract continue using the handle and also participates in the user decrypt authorization path. `allow(value, user)` lets the specified user decrypt.

## Successful User Decrypt

```ts
const handle = await vault.balanceOf(alice.address);
const clear = await fhevm.userDecryptEuint(FhevmType.euint64, handle, vaultAddress, alice);
expect(clear).to.eq(100n);
```

The type must match the Solidity encrypted type:

| Solidity | Helper |
| --- | --- |
| `ebool` | `userDecryptEbool(handle, contract, signer)` |
| `euintXX` | `userDecryptEuint(FhevmType.euintXX, handle, contract, signer)` |
| `eaddress` | `userDecryptEaddress(handle, contract, signer)` |

## Unauthorized User Failure

```ts
let failed = false;
try {
  await fhevm.userDecryptEuint(FhevmType.euint64, handle, vaultAddress, bob);
} catch {
  failed = true;
}
expect(failed).to.eq(true);
```

## recipient / spender / operator

For transfer-like contracts, test at least:

- the sender can still decrypt their own balance after sending.
- the recipient can decrypt their balance after receiving.
- third parties cannot decrypt sender/recipient balances.
- if an operator only needs temporary on-chain use, long-lived user decrypt should not be authorized.

## debugger Is Not an ACL Test

```ts
const clear = await fhevm.debugger.decryptEuint(FhevmType.euint64, handle);
```

This API is only appropriate for debugging computation results in mock mode. It does not prove that `FHE.allow` is correct. Permission-sensitive tests must use `userDecrypt*`.

## Common Mistakes

- Forgetting `FHE.allowThis`.
- Authorizing only `msg.sender` and forgetting the recipient.
- Using the wrong `FhevmType`, such as decrypting an `euint64` as an `euint32`.
- Passing the wrong contract address. The `contract` parameter for user decrypt must be the contract with ACL permissions.
- Running mock-only debugger assertions on Sepolia.
