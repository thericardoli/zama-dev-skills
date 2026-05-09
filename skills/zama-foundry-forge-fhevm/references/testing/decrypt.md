# Testing Decrypt

In FHEVM, "decryption" is not a single test objective. Choose the path first:

| What you want to prove | Use | Checks ACL? |
| --- | --- | --- |
| Encrypted computation result is correct | `decrypt(value)` | No |
| A result can be public and the KMS proof verifies | `publicDecrypt(handles)` | Checks the public-decrypt flag |
| Custom callback/finalize proof encoding is correct | `buildDecryptionProof(handles, encoded)` | No |
| A specific user can read their own handle | `signUserDecrypt` + `userDecrypt` | Checks persistent ACL and signature |

## Direct Decrypt: Test Only Computation Results

```solidity
function test_deposit_updatesBalance() public {
    (externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(vault));
    vault.deposit(amount, proof);

    assertEq(decrypt(vault.balanceOf(address(this))), 100);
}
```

`decrypt` is a test backdoor. It reads the local plaintext database maintained by `forge-fhevm` and does not check:

- `FHE.allowThis`
- `FHE.allow(user)`
- public-decrypt flag
- user signature

Direct decrypt is therefore a good first-layer quick test, but it is not a substitute for permission tests.

Typed overloads:

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

## Public Decrypt: Test Public Results

Application contracts usually mark a result as publicly decryptable first:

```solidity
function allowBalanceForPublicDecrypt(address account) external {
    FHE.makePubliclyDecryptable(_balances[account]);
}
```

If the contract also verifies the KMS proof on-chain:

```solidity
function verifyPublicDecrypt(
    bytes32[] memory handles,
    bytes memory abiEncodedCleartexts,
    bytes memory proof
) external {
    FHE.checkSignatures(handles, abiEncodedCleartexts, proof);
}
```

Test:

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

Important details of `publicDecrypt`:

- Every handle must already be marked as public decryptable.
- It returns `uint256[] cleartexts`.
- The proof is generated for `abi.encode(cleartexts)`.
- Handle order and cleartext order must match.

It should fail before a handle is marked:

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

`publicDecrypt` is internal; an external wrapper makes it easier to catch the revert selector.

## buildDecryptionProof: Test Custom Callback Encoding

If the contract callback verifies something other than `abi.encode(uint256[])`, do not reuse the proof from `publicDecrypt`.

For example, if the contract wants to verify:

```solidity
abi.encode(winner, amount)
```

the test should use:

```solidity
bytes32[] memory handles = new bytes32[](2);
handles[0] = winnerHandle;
handles[1] = amountHandle;

bytes memory encoded = abi.encode(winner, amount);
bytes memory proof = buildDecryptionProof(handles, encoded);

auction.finalize(handles, encoded, proof);
```

`buildDecryptionProof` only generates a proof. It does not check ACL and does not prove that public disclosure is allowed by the application. Callback tests should also cover:

- Whether the request id matches.
- Whether the expected handles match.
- Whether finalize can execute only once.
- Whether caller, deadline, and state machine checks are correct.

## User Decrypt: Test the Real User Read Path

The contract side must grant two persistent ACL entries for the handle:

```solidity
FHE.allowThis(value);
FHE.allow(value, user);
```

Test:

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

This test proves:

- The user has persistent ACL on the handle.
- The contract itself has persistent ACL on the handle.
- The signature user matches the user passed to `userDecrypt`.
- The contract authorized by the signature matches the contract passed to `userDecrypt`.

## User Decrypt Failure Paths

`userDecrypt` checks:

- `userAddress != contractAddress`
- The user has persistent ACL
- The contract has persistent ACL
- The signature recovers to the user

Missing `allowThis`:

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

Wrapper:

```solidity
function callUserDecrypt(bytes32 handle, address user, address contractAddress, bytes memory sig)
    external
    returns (uint256)
{
    return userDecrypt(handle, user, contractAddress, sig);
}
```

## Common Misconceptions

- Passing `decrypt` does not mean `userDecrypt` will succeed.
- Passing `buildDecryptionProof` does not mean the handle is allowed for public decrypt.
- The proof returned by `publicDecrypt` matches `abi.encode(uint256[])` by default, not custom callback encoding.
- Granting `allow` to the user but forgetting `allowThis`.
- Authorizing only the sender after a transfer and forgetting the recipient.
