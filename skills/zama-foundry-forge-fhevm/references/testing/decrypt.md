# 测试 decrypt

FHEVM 里“解密”不是一件事，而是几种不同测试目的。先选路径：

| 你想证明什么 | 用什么 | 是否检查 ACL |
| --- | --- | --- |
| encrypted 计算结果对不对 | `decrypt(value)` | 不检查 |
| 结果可以公开且 KMS proof 能验证 | `publicDecrypt(handles)` | 检查 public decrypt flag |
| 自定义 callback/finalize proof 编码正确 | `buildDecryptionProof(handles, encoded)` | 不检查 |
| 某个用户能读取自己的 handle | `signUserDecrypt` + `userDecrypt` | 检查 persistent ACL 和签名 |

## Direct decrypt：只测计算结果

```solidity
function test_deposit_updatesBalance() public {
    (externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(vault));
    vault.deposit(amount, proof);

    assertEq(decrypt(vault.balanceOf(address(this))), 100);
}
```

`decrypt` 是测试后门。它读取 `forge-fhevm` 的本地 plaintext DB，不检查：

- `FHE.allowThis`
- `FHE.allow(user)`
- public decrypt flag
- user signature

所以 direct decrypt 适合作为第一层快速测试，但不能作为权限测试的替代。

typed overloads：

```solidity
bool clearBool = decrypt(encryptedBool);
uint8 clear8 = decrypt(encryptedUint8);
uint16 clear16 = decrypt(encryptedUint16);
uint32 clear32 = decrypt(encryptedUint32);
uint64 clear64 = decrypt(encryptedUint64);
uint128 clear128 = decrypt(encryptedUint128);
uint256 clear256 = decrypt(encryptedUint256);
address clearAddress = decrypt(encryptedAddress);
```

## Public decrypt：测公开结果

业务合约通常先标记某个结果可以公开：

```solidity
function allowBalanceForPublicDecrypt(address account) external {
    FHE.makePubliclyDecryptable(_balances[account]);
}
```

如果合约还要链上验证 KMS proof：

```solidity
function verifyPublicDecrypt(
    bytes32[] memory handles,
    bytes memory abiEncodedCleartexts,
    bytes memory proof
) external {
    FHE.checkSignatures(handles, abiEncodedCleartexts, proof);
}
```

测试：

```solidity
function test_publicDecrypt_balance() public {
    (externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(vault));
    vault.deposit(amount, proof);
    vault.allowBalanceForPublicDecrypt(address(this));

    bytes32[] memory handles = new bytes32[](1);
    handles[0] = euint64.unwrap(vault.balanceOf(address(this)));

    (uint256[] memory cleartexts, bytes memory decryptionProof) = publicDecrypt(handles);

    assertEq(cleartexts[0], 100);
    vault.verifyPublicDecrypt(handles, abi.encode(cleartexts), decryptionProof);
}
```

`publicDecrypt` 的重要细节：

- 它要求每个 handle 已经被标记为 public decryptable。
- 它返回 `uint256[] cleartexts`。
- proof 是针对 `abi.encode(cleartexts)` 生成的。
- handles 顺序和 cleartexts 顺序必须一致。

未标记时应失败：

```solidity
function test_publicDecrypt_revertsWithoutPublicFlag() public {
    (externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(vault));
    vault.deposit(amount, proof);

    bytes32[] memory handles = new bytes32[](1);
    handles[0] = euint64.unwrap(vault.balanceOf(address(this)));

    vm.expectRevert(abi.encodeWithSelector(HandleNotAllowedForPublicDecryption.selector, handles[0]));
    this.callPublicDecrypt(handles);
}

function callPublicDecrypt(bytes32[] memory handles)
    external
    returns (uint256[] memory, bytes memory)
{
    return publicDecrypt(handles);
}
```

`publicDecrypt` 是 internal；用 external wrapper 更容易捕捉 revert selector。

## buildDecryptionProof：测自定义 callback 编码

如果合约 callback 验证的不是 `abi.encode(uint256[])`，不要直接复用 `publicDecrypt` 的 proof。

例如合约想验证：

```solidity
abi.encode(winner, amount)
```

测试应使用：

```solidity
bytes32[] memory handles = new bytes32[](2);
handles[0] = winnerHandle;
handles[1] = amountHandle;

bytes memory encoded = abi.encode(winner, amount);
bytes memory proof = buildDecryptionProof(handles, encoded);

auction.finalize(handles, encoded, proof);
```

`buildDecryptionProof` 只生成 proof，不检查 ACL，也不证明业务上允许公开。callback 测试还要覆盖：

- request id 是否匹配。
- expected handles 是否匹配。
- finalize 是否只能执行一次。
- caller、deadline、状态机是否正确。

## User decrypt：测用户真实读取路径

合约侧需要给 handle 两种 persistent ACL：

```solidity
FHE.allowThis(value);
FHE.allow(value, user);
```

测试：

```solidity
function test_userDecrypt_balance() public {
    uint256 userPk = 0xA11CE;
    address user = vm.addr(userPk);

    (externalEuint64 amount, bytes memory proof) = encryptUint64(222, user, address(vault));

    vm.prank(user);
    vault.deposit(amount, proof);

    euint64 balance = vault.balanceOf(user);
    bytes memory signature = signUserDecrypt(userPk, address(vault));
    uint256 clear = userDecrypt(euint64.unwrap(balance), user, address(vault), signature);

    assertEq(clear, 222);
}
```

这个测试证明：

- 用户对 handle 有 persistent ACL。
- 合约自身对 handle 有 persistent ACL。
- 签名 user 和 `userDecrypt` 传入的 user 一致。
- 签名授权的 contract 和 `userDecrypt` 传入的 contract 一致。

## User decrypt 失败路径

`userDecrypt` 会检查：

- `userAddress != contractAddress`
- user 有 persistent ACL
- contract 有 persistent ACL
- signature recover 到 user

缺少 `allowThis`：

```solidity
function test_userDecrypt_revertsWithoutAllowThis() public {
    uint256 userPk = 0xA11CE;
    address user = vm.addr(userPk);

    euint64 value = badVault.valueAllowedOnlyToUser(user);
    bytes memory sig = signUserDecrypt(userPk, address(badVault));

    vm.expectRevert(
        abi.encodeWithSelector(
            ContractNotAuthorizedForDecrypt.selector,
            euint64.unwrap(value),
            address(badVault)
        )
    );
    this.callUserDecrypt(euint64.unwrap(value), user, address(badVault), sig);
}
```

wrapper：

```solidity
function callUserDecrypt(bytes32 handle, address user, address contractAddress, bytes memory sig)
    external
    returns (uint256)
{
    return userDecrypt(handle, user, contractAddress, sig);
}
```

## 常见误区

- `decrypt` 测过了，不代表 `userDecrypt` 会成功。
- `buildDecryptionProof` 能过，不代表 handle 被允许 public decrypt。
- `publicDecrypt` 的 proof 默认匹配 `abi.encode(uint256[])`，不匹配自定义 callback 编码。
- 只给 user `allow`，忘了 `allowThis`。
- transfer 后只授权 sender，忘了 recipient。
