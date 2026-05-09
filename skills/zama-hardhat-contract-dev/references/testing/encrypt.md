# Testing Encrypted Input

In Hardhat tests, encrypted input comes from:

```ts
const encrypted = await fhevm
  .createEncryptedInput(contractAddress, user.address)
  .add64(100n)
  .encrypt();
```

Calling the contract:

```ts
await vault.connect(user).deposit(encrypted.handles[0], encrypted.inputProof);
```

## Target Binding

`contractAddress` must be the contract that executes `FHE.fromExternal`.

```ts
const encrypted = await fhevm
  .createEncryptedInput(otherVaultAddress, alice.address)
  .add64(100n)
  .encrypt();

await expect(vault.connect(alice).deposit(encrypted.handles[0], encrypted.inputProof))
  .to.be.reverted;
```

This input proof proves that `otherVaultAddress` may consume the handle, not `vaultAddress`.

## User Binding

`userAddress` must match the signer that sends the transaction.

```ts
const encrypted = await fhevm
  .createEncryptedInput(vaultAddress, bob.address)
  .add64(100n)
  .encrypt();

await expect(vault.connect(alice).deposit(encrypted.handles[0], encrypted.inputProof))
  .to.be.reverted;
```

## Multi-Value Input

```ts
const input = fhevm.createEncryptedInput(orderBookAddress, alice.address);
input.addAddress(token.address);
input.add64(100n);
input.addBool(true);
const enc = await input.encrypt();

await orderBook
  .connect(alice)
  .submit(enc.handles[0], enc.handles[1], enc.handles[2], enc.inputProof);
```

Deliberately swap `handles[1]` and `handles[2]` in tests. The call should fail or produce an invalid type; it must not silently succeed.

## Boundary Values

Cover:

- `0`
- `1`
- the type's maximum value, such as `2n ** 64n - 1n`
- out-of-range input, which should fail in the TypeScript builder
- insufficient-balance or underflow business paths

Example:

```ts
let failed = false;
try {
  await fhevm.createEncryptedInput(vaultAddress, alice.address).add64(2n ** 64n).encrypt();
} catch {
  failed = true;
}
expect(failed).to.eq(true);
```
