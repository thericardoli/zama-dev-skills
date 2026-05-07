# 测试 encrypted input

Hardhat 测试里 encrypted input 来自：

```ts
const encrypted = await fhevm
  .createEncryptedInput(contractAddress, user.address)
  .add64(100n)
  .encrypt();
```

调用合约：

```ts
await vault.connect(user).deposit(encrypted.handles[0], encrypted.inputProof);
```

## target 绑定

`contractAddress` 必须是执行 `FHE.fromExternal` 的合约。

```ts
const encrypted = await fhevm
  .createEncryptedInput(otherVaultAddress, alice.address)
  .add64(100n)
  .encrypt();

await expect(vault.connect(alice).deposit(encrypted.handles[0], encrypted.inputProof))
  .to.be.reverted;
```

这个输入 proof 证明的是 `otherVaultAddress` 可消费该 handle，不是 `vaultAddress`。

## user 绑定

`userAddress` 必须和发送交易的 signer 匹配。

```ts
const encrypted = await fhevm
  .createEncryptedInput(vaultAddress, bob.address)
  .add64(100n)
  .encrypt();

await expect(vault.connect(alice).deposit(encrypted.handles[0], encrypted.inputProof))
  .to.be.reverted;
```

## 多值输入

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

测试时故意交换 `handles[1]` 和 `handles[2]`，应该失败或产生错误类型，不应默默成功。

## 边界值

覆盖：

- `0`
- `1`
- 类型最大值，例如 `2n ** 64n - 1n`
- 超范围输入在 TypeScript builder 阶段应失败
- 余额不足或 underflow 业务路径

示例：

```ts
let failed = false;
try {
  await fhevm.createEncryptedInput(vaultAddress, alice.address).add64(2n ** 64n).encrypt();
} catch {
  failed = true;
}
expect(failed).to.eq(true);
```
