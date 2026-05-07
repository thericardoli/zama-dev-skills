# 测试 public decrypt

只有结果本来就应该公开时才 public decrypt。

合约侧：

```solidity
event ResultRequested(euint64 result);

euint64 private _result;

function requestResult() external {
    FHE.makePubliclyDecryptable(_result);
    emit ResultRequested(_result);
}
```

测试侧：

```ts
await vault.requestResult();
const handle = await vault.result();
const clear = await fhevm.publicDecryptEuint(FhevmType.euint64, handle);
expect(clear).to.eq(100n);
```

## 未标记 public 应失败

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

## 类型

```ts
await fhevm.publicDecryptEbool(handle);
await fhevm.publicDecryptEuint(FhevmType.euint32, handle);
await fhevm.publicDecryptEaddress(handle);
```

generic：

```ts
const result = await fhevm.publicDecrypt([handle0, handle1]);
const clear0 = result.clearValues[handle0];
```

## 链上 finalize

如果合约有 `finalize(clear, proof)` 并调用 `FHE.checkSignatures`，Hardhat plugin 的 high-level `publicDecryptEuint` 只返回 clear value，不直接给 Solidity callback proof。测试这类流程时：

- 优先按项目已有 Zama SDK 或 relayer runtime callback helper。
- 或在 mock/debug 层使用 `fhevm.debugger.createDecryptionSignatures(handles, clearValues)` 生成签名参数。
- 覆盖错 handle、错 cleartext、重复 finalize、未 request finalize。

不要把 user decrypt 签名拿来当 public decrypt callback proof。
