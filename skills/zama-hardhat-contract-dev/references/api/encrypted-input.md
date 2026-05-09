# Encrypted Input API

Core API:

```ts
const input = fhevm.createEncryptedInput(contractAddress, userAddress);
input.add64(100n);
const encrypted = await input.encrypt();
```

`contractAddress` must be the address of the contract that ultimately calls `FHE.fromExternal`. `userAddress` must be the address of the signer that sends the transaction.

## Supported add Methods

| Solidity external type | TypeScript add | Plaintext type |
| --- | --- | --- |
| `externalEbool` | `addBool(value)` | `boolean | number | bigint`; accepts only 0/1 or bool |
| `externalEuint8` | `add8(value)` | `number | bigint` |
| `externalEuint16` | `add16(value)` | `number | bigint` |
| `externalEuint32` | `add32(value)` | `number | bigint` |
| `externalEuint64` | `add64(value)` | `number | bigint` |
| `externalEuint128` | `add128(value)` | `number | bigint` |
| `externalEuint256` | `add256(value)` | `number | bigint` |
| `externalEaddress` | `addAddress(value)` | checksum-able address string |

The current mock-utils types do not expose `add4`. Even though `FhevmType.euint4` exists, do not assume the external input builder supports it.

## Return Value

```ts
const encrypted = await input.encrypt();
encrypted.handles[0]; // bytes32-like handle accepted by ethers
encrypted.inputProof; // bytes-like proof
```

Handles returned by the mock environment are usually `Uint8Array` values and can be passed directly to contract `bytes32` parameters. Convert first if you need to print them, use them as map keys, or pass them to helpers that accept only hex strings:

```ts
const handle = ethers.hexlify(encrypted.handles[0]);
```

Passing to Solidity:

```ts
await vault.connect(alice).deposit(encrypted.handles[0], encrypted.inputProof);
```

## Multi-Value Input

The handle order must match the Solidity parameter semantics:

```ts
const input = fhevm.createEncryptedInput(contractAddress, alice.address);
input.addBool(true);
input.add64(100n);
input.addAddress(recipient.address);
const enc = await input.encrypt();

await contract
  .connect(alice)
  .submit(enc.handles[0], enc.handles[1], enc.handles[2], enc.inputProof);
```

## Overloaded Functions

`externalEuint64` often appears as `bytes32` in the ABI. In ERC7984 or heavily overloaded contracts, select the function signature explicitly:

```ts
await token
  .connect(alice)
  ["confidentialTransfer(address,bytes32,bytes)"](
    bob.address,
    encrypted.handles[0],
    encrypted.inputProof,
  );
```

## Failure Paths

All of the following should fail:

```ts
const wrongTarget = await fhevm
  .createEncryptedInput(otherContractAddress, alice.address)
  .add64(100n)
  .encrypt();

await expect(vault.connect(alice).deposit(wrongTarget.handles[0], wrongTarget.inputProof))
  .to.be.reverted;
```

```ts
const wrongUser = await fhevm
  .createEncryptedInput(vaultAddress, bob.address)
  .add64(100n)
  .encrypt();

await expect(vault.connect(alice).deposit(wrongUser.handles[0], wrongUser.inputProof))
  .to.be.reverted;
```

Target and user binding mistakes are among the most common issues in Hardhat FHEVM tests.
