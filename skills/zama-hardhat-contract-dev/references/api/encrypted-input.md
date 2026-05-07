# Encrypted Input API

核心 API：

```ts
const input = fhevm.createEncryptedInput(contractAddress, userAddress);
input.add64(100n);
const encrypted = await input.encrypt();
```

`contractAddress` 必须是最终调用 `FHE.fromExternal` 的合约地址。`userAddress` 必须是发起交易的 signer 地址。

## 支持的 add 方法

| Solidity 外部类型 | TypeScript add | 明文类型 |
| --- | --- | --- |
| `externalEbool` | `addBool(value)` | `boolean | number | bigint`，只接受 0/1 或 bool |
| `externalEuint8` | `add8(value)` | `number | bigint` |
| `externalEuint16` | `add16(value)` | `number | bigint` |
| `externalEuint32` | `add32(value)` | `number | bigint` |
| `externalEuint64` | `add64(value)` | `number | bigint` |
| `externalEuint128` | `add128(value)` | `number | bigint` |
| `externalEuint256` | `add256(value)` | `number | bigint` |
| `externalEaddress` | `addAddress(value)` | checksum-able address string |

当前 mock-utils 类型里没有 `add4`，即使 `FhevmType.euint4` 存在，也不要假设 external input builder 支持它。

## 返回值

```ts
const encrypted = await input.encrypt();
encrypted.handles[0]; // ethers 可接受的 bytes32-like handle
encrypted.inputProof; // bytes-like proof
```

mock 返回的 handle 通常是 `Uint8Array`，可以直接传给合约的 `bytes32` 参数。若要打印、作为 map key，或传给只收 hex string 的 helper，先做转换：

```ts
const handle = ethers.hexlify(encrypted.handles[0]);
```

传给 Solidity：

```ts
await vault.connect(alice).deposit(encrypted.handles[0], encrypted.inputProof);
```

## 多值输入

handles 顺序必须和 Solidity 参数语义一致：

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

## 重载函数

`externalEuint64` 在 ABI 中常显示为 `bytes32`。ERC7984 或多重载合约中，显式选择签名：

```ts
await token
  .connect(alice)
  ["confidentialTransfer(address,bytes32,bytes)"](
    bob.address,
    encrypted.handles[0],
    encrypted.inputProof,
  );
```

## 错误路径

这些都应该失败：

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

target 和 user 绑定错误是 Hardhat FHEVM 测试里最常见的问题。
