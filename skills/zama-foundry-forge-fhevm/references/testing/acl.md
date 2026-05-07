# 测试 ACL

ACL 测试回答的问题是：

```text
这个 encrypted handle，谁能继续参与链上计算，谁能 user decrypt，谁能 public decrypt？
```

`decrypt(...)` 不检查 ACL，所以 ACL 测试必须用 `userDecrypt`、`publicDecrypt`、失败路径和跨合约调用来证明权限真的正确。

## 授权有三类

| 授权 | 用途 | 测试方式 |
| --- | --- | --- |
| `FHE.allowThis(value)` | 合约后续还能使用/参与 user decrypt | `userDecrypt` 缺它会失败 |
| `FHE.allow(value, user)` | 用户能 user decrypt | 用对应 user `userDecrypt` |
| `FHE.allowTransient(value, target)` | 同一交易内给另一个合约临时使用 | 测跨合约调用成功/失败 |
| `FHE.makePubliclyDecryptable(value)` | 所有人可 public decrypt | 用 `publicDecrypt` |

每次生成新 ciphertext，都要重新考虑权限传播。旧 handle 的授权不会自动搬到新 handle 上。

## 保存状态后的基本测试

合约：

```solidity
function deposit(externalEuint64 encryptedAmount, bytes calldata proof) external {
    euint64 amount = FHE.fromExternal(encryptedAmount, proof);
    euint64 next = FHE.add(_balances[msg.sender], amount);

    _balances[msg.sender] = next;
    FHE.allowThis(next);
    FHE.allow(next, msg.sender);
}
```

测试：

```solidity
function test_deposit_grantsUserDecryptAcl() public {
    uint256 userPk = 0xA11CE;
    address user = vm.addr(userPk);

    (externalEuint64 amount, bytes memory proof) = encryptUint64(100, user, address(vault));

    vm.prank(user);
    vault.deposit(amount, proof);

    bytes memory sig = signUserDecrypt(userPk, address(vault));
    uint256 clear = userDecrypt(euint64.unwrap(vault.balanceOf(user)), user, address(vault), sig);

    assertEq(clear, 100);
}
```

这个测试同时证明 `allowThis` 和 `allow(user)` 都存在。少任何一个，`userDecrypt` 都应失败。

## 专门测缺少 allowThis

这是最容易被 `decrypt` 掩盖的问题。

```solidity
function test_userDecrypt_failsWithoutAllowThis() public {
    uint256 userPk = 0xA11CE;
    address user = vm.addr(userPk);

    (externalEuint64 amount, bytes memory proof) = encryptUint64(100, user, address(badVault));

    vm.prank(user);
    badVault.depositWithoutAllowThis(amount, proof);

    euint64 balance = badVault.balanceOf(user);
    bytes memory sig = signUserDecrypt(userPk, address(badVault));

    vm.expectRevert(
        abi.encodeWithSelector(
            ContractNotAuthorizedForDecrypt.selector,
            euint64.unwrap(balance),
            address(badVault)
        )
    );
    this.callUserDecrypt(euint64.unwrap(balance), user, address(badVault), sig);
}
```

## 专门测缺少 user allow

```solidity
function test_userDecrypt_failsWithoutUserAllow() public {
    uint256 userPk = 0xA11CE;
    address user = vm.addr(userPk);

    (externalEuint64 amount, bytes memory proof) = encryptUint64(100, user, address(badVault));

    vm.prank(user);
    badVault.depositWithoutUserAllow(amount, proof);

    euint64 balance = badVault.balanceOf(user);
    bytes memory sig = signUserDecrypt(userPk, address(badVault));

    vm.expectRevert(
        abi.encodeWithSelector(UserNotAuthorizedForDecrypt.selector, euint64.unwrap(balance), user)
    );
    this.callUserDecrypt(euint64.unwrap(balance), user, address(badVault), sig);
}
```

## 转账权限传播

转账要更新两个新 handle：sender 新余额和 recipient 新余额。两边都要重新授权。

```solidity
function transfer(address to, externalEuint64 encryptedAmount, bytes calldata proof) external {
    euint64 amount = FHE.fromExternal(encryptedAmount, proof);

    ebool canTransfer = FHE.ge(_balances[msg.sender], amount);
    euint64 nextSender = FHE.select(canTransfer, FHE.sub(_balances[msg.sender], amount), _balances[msg.sender]);
    euint64 nextRecipient = FHE.select(canTransfer, FHE.add(_balances[to], amount), _balances[to]);

    _balances[msg.sender] = nextSender;
    _balances[to] = nextRecipient;

    FHE.allowThis(nextSender);
    FHE.allowThis(nextRecipient);
    FHE.allow(nextSender, msg.sender);
    FHE.allow(nextRecipient, to);
}
```

测试：

```solidity
function test_transfer_grantsRecipientBalanceAcl() public {
    uint256 alicePk = 0xA11CE;
    uint256 bobPk = 0xB0B;
    address alice = vm.addr(alicePk);
    address bob = vm.addr(bobPk);

    _mint(alice, 1000);

    (externalEuint64 amount, bytes memory proof) = encryptUint64(400, alice, address(token));

    vm.prank(alice);
    token.transfer(bob, amount, proof);

    assertEq(_userDecryptBalance(alicePk, alice), 600);
    assertEq(_userDecryptBalance(bobPk, bob), 400);
}

function _userDecryptBalance(uint256 pk, address account) internal returns (uint64) {
    bytes memory sig = signUserDecrypt(pk, address(token));
    return uint64(userDecrypt(
        euint64.unwrap(token.balanceOf(account)),
        vm.addr(pk),
        address(token),
        sig
    ));
}
```

如果 sender 也需要知道 recipient 的新余额，合约必须额外授权 sender。不要默认 sender 能解密 recipient 的状态。

## Public decrypt flag

业务合约通常用：

```solidity
FHE.makePubliclyDecryptable(value);
```

测试正反两条路径：

```solidity
function test_publicDecrypt_requiresPublicFlag() public {
    _deposit(address(this), 100);

    bytes32[] memory handles = new bytes32[](1);
    handles[0] = euint64.unwrap(vault.balanceOf(address(this)));

    vm.expectRevert(abi.encodeWithSelector(HandleNotAllowedForPublicDecryption.selector, handles[0]));
    this.callPublicDecrypt(handles);

    vault.allowBalanceForPublicDecrypt(address(this));
    (uint256[] memory cleartexts,) = publicDecrypt(handles);
    assertEq(cleartexts[0], 100);
}
```

底层 host contract 测试可以直接调用 `_acl.allowForDecryption(handles)`。业务合约测试优先走 `FHE.makePubliclyDecryptable`。

## Transient ACL

`allowTransient` 是同一交易内的临时权限。它不等价于 `allow`，也不能用于 user decrypt。

测试重点：

```solidity
function test_userDecrypt_failsWithOnlyTransientAllow() public {
    vm.expectRevert(abi.encodeWithSelector(UserNotAuthorizedForDecrypt.selector, handle, user));
    this.callUserDecrypt(handle, user, address(vault), sig);
}
```

跨合约组合测试应覆盖：

- 不调用 `FHE.allowTransient(value, target)` 时，下游合约无法使用 handle。
- 调用后，同一交易内下游合约可以使用 handle。
- 下一笔交易不能继续依赖 transient 权限。

## 接收已有 handle

如果函数接收已有 `euintXX`，而不是本次 `FHE.fromExternal` 创建的新 input，要检查 sender 是否有权使用：

```solidity
function consumeExisting(euint64 amount) external {
    if (!FHE.isSenderAllowed(amount)) {
        revert UnauthorizedHandle();
    }

    _total = FHE.add(_total, amount);
    FHE.allowThis(_total);
}
```

测试思路：

```solidity
function test_consumeExisting_revertsForUnauthorizedHandle() public {
    euint64 amount = producer.makeAmountFor(alice);

    vm.prank(bob);
    vm.expectRevert(UnauthorizedHandle.selector);
    consumer.consumeExisting(amount);
}
```

## 排错表

| 现象 | 先查什么 |
| --- | --- |
| `decrypt` 通过，`userDecrypt` 失败 | `allowThis` 和 `allow(user)` |
| `UserNotAuthorizedForDecrypt` | 是否授权了 user，是否只有 transient |
| `ContractNotAuthorizedForDecrypt` | 是否调用 `FHE.allowThis` |
| recipient 解不了转账后的余额 | 是否授权了 recipient 的新 handle |
| public decrypt 失败 | 是否调用 `makePubliclyDecryptable`，handles 是否正确 |
| 跨合约 FHE 运算失败 | 是否给目标合约 `allowTransient` |
| 下一笔交易 transient 权限失效 | 这是预期，需要 persistent `allow` |
