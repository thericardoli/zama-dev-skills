# Testing ACL

ACL tests answer this question:

```text
For this encrypted handle, who can continue using it in on-chain computation, who can user-decrypt it, and who can public-decrypt it?
```

`decrypt(...)` does not check ACL, so ACL tests must use `userDecrypt`, `publicDecrypt`, failure paths, and cross-contract calls to prove that permissions are actually correct.

## Four Authorization Types

| Authorization | Purpose | How to test |
| --- | --- | --- |
| `FHE.allowThis(value)` | Lets the contract keep using the value and participate in user decrypt | `userDecrypt` fails without it |
| `FHE.allow(value, user)` | Lets the user perform user decrypt | Call `userDecrypt` as that user |
| `FHE.allowTransient(value, target)` | Temporarily grants another contract access within the same transaction | Test cross-contract call success/failure |
| `FHE.makePubliclyDecryptable(value)` | Lets anyone public-decrypt the value | Use `publicDecrypt` |

Every time a new ciphertext is produced, revisit permission propagation. Authorizations on the old handle are not automatically transferred to the new handle.

## Basic Test After Storing State

Contract:

```solidity
function deposit(externalEuint64 encryptedAmount, bytes calldata proof) external {
    euint64 amount = FHE.fromExternal(encryptedAmount, proof);
    euint64 next = FHE.add(_balances[msg.sender], amount);

    _balances[msg.sender] = next;
    FHE.allowThis(next);
    FHE.allow(next, msg.sender);
}
```

Test:

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

This test proves that both `allowThis` and `allow(user)` are present. If either is missing, `userDecrypt` should fail.

## Specifically Test Missing allowThis

This is the easiest issue for `decrypt` to hide.

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

## Specifically Test Missing User allow

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

## Transfer Permission Propagation

A transfer updates two new handles: the sender's new balance and the recipient's new balance. Both sides must be authorized again.

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

Test:

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

If the sender also needs to know the recipient's new balance, the contract must grant the sender separately. Do not assume the sender can decrypt the recipient's state by default.

## Public Decrypt Flag

Application contracts usually call:

```solidity
FHE.makePubliclyDecryptable(value);
```

Test both positive and negative paths:

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

Low-level host contract tests may call `_acl.allowForDecryption(handles)` directly. Application contract tests should prefer `FHE.makePubliclyDecryptable`.

## Transient ACL

`allowTransient` is a same-transaction temporary permission. It is not equivalent to `allow`, and it cannot be used for user decrypt.

Core test:

```solidity
function test_userDecrypt_failsWithOnlyTransientAllow() public {
    vm.expectRevert(abi.encodeWithSelector(UserNotAuthorizedForDecrypt.selector, handle, user));
    this.callUserDecrypt(handle, user, address(vault), sig);
}
```

Cross-contract composition tests should cover:

- Without `FHE.allowTransient(value, target)`, the downstream contract cannot use the handle.
- After it is called, the downstream contract can use the handle within the same transaction.
- The next transaction cannot rely on transient permission.

## Receiving Existing Handles

If a function receives an existing `euintXX` instead of a new input created by this call's `FHE.fromExternal`, check whether the sender is allowed to use it:

```solidity
function consumeExisting(euint64 amount) external {
    if (!FHE.isSenderAllowed(amount)) {
        revert UnauthorizedHandle();
    }

    _total = FHE.add(_total, amount);
    FHE.allowThis(_total);
}
```

Test idea:

```solidity
function test_consumeExisting_revertsForUnauthorizedHandle() public {
    euint64 amount = producer.makeAmountFor(alice);

    vm.prank(bob);
    vm.expectRevert(UnauthorizedHandle.selector);
    consumer.consumeExisting(amount);
}
```

## Troubleshooting Table

| Symptom | Check first |
| --- | --- |
| `decrypt` passes, `userDecrypt` fails | `allowThis` and `allow(user)` |
| `UserNotAuthorizedForDecrypt` | Whether the user was authorized, and whether only transient permission was granted |
| `ContractNotAuthorizedForDecrypt` | Whether `FHE.allowThis` was called |
| Recipient cannot decrypt post-transfer balance | Whether the recipient's new handle was authorized |
| Public decrypt fails | Whether `makePubliclyDecryptable` was called and whether handles are correct |
| Cross-contract FHE operation fails | Whether the target contract was granted `allowTransient` |
| Transient permission disappears in the next transaction | This is expected; use persistent `allow` when needed |
