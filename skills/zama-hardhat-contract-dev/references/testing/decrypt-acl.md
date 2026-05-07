# 测试 decrypt 和 ACL

合约侧写入新 handle 后要设置：

```solidity
FHE.allowThis(value);
FHE.allow(value, user);
```

`allowThis` 允许合约继续使用 handle，也参与 user decrypt 授权路径。`allow(value, user)` 允许指定用户解密。

## 正向 user decrypt

```ts
const handle = await vault.balanceOf(alice.address);
const clear = await fhevm.userDecryptEuint(FhevmType.euint64, handle, vaultAddress, alice);
expect(clear).to.eq(100n);
```

类型必须匹配 Solidity encrypted 类型：

| Solidity | Helper |
| --- | --- |
| `ebool` | `userDecryptEbool(handle, contract, signer)` |
| `euintXX` | `userDecryptEuint(FhevmType.euintXX, handle, contract, signer)` |
| `eaddress` | `userDecryptEaddress(handle, contract, signer)` |

## 未授权用户失败

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

转账类合约至少测：

- sender 转出后仍能解密自己的余额。
- recipient 能解密收到后的余额。
- 第三方不能解密 sender/recipient 的余额。
- operator 如果只需要链上临时使用，应测试长期 user decrypt 不被授权。

## debugger 不等于 ACL 测试

```ts
const clear = await fhevm.debugger.decryptEuint(FhevmType.euint64, handle);
```

这个 API 只适合 mock 排查运算结果。它不证明 `FHE.allow` 正确。涉及权限必须使用 `userDecrypt*`。

## 常见错误

- 忘记 `FHE.allowThis`。
- 只给 `msg.sender` 授权，忘记 recipient。
- 用错 `FhevmType`，例如把 `euint64` 按 `euint32` 解。
- 合约 address 传错，user decrypt 的 contract 参数必须是有 ACL 权限的合约。
- 在 Sepolia 上跑 mock-only debugger 断言。
