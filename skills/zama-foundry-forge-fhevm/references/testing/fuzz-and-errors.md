# Fuzzing, Boundaries, and Common Errors

Fuzz tests should not randomize only the success path. For FHEVM contracts, fuzzing is most valuable when it covers:

- Fixed-width integer wrapping.
- Boundaries around encrypted comparisons plus `FHE.select`.
- Zero/uninitialized handles.
- Wrong user, wrong target, and wrong ACL.
- Public/user decrypt failure paths.

## What Wrapping Means

FHE integer types such as `euint8`, `euint16`, and `euint64` have fixed bit widths. When a result exceeds the range, semantics usually match same-width unsigned integer wrapping.

Examples:

```text
euint8: 255 + 1 = 0
euint8: 250 + 10 = 4
euint8: 0 - 1 = 255
```

When testing `euint64` addition, compute the expected value with `uint64` semantics:

```solidity
uint64 expected;
unchecked {
    expected = a + b;
}
```

For balances, allowances, and supply, wrapping is usually not acceptable at the business-logic level. Contracts should use encrypted comparisons and `FHE.select` so failure paths preserve the original state.

## Arithmetic Fuzzing

Good fit for pure FHE arithmetic helpers:

```solidity
function test_add_fuzz(uint64 a, uint64 b) public {
    (externalEuint64 left, bytes memory leftProof) = encryptUint64(a, address(adder));
    (externalEuint64 right, bytes memory rightProof) = encryptUint64(b, address(adder));

    euint64 sum = adder.add(left, leftProof, right, rightProof);

    uint64 expected;
    unchecked {
        expected = a + b;
    }

    assertEq(decrypt(sum), expected);
}
```

This test treats wrapping as part of the low-level operation semantics.

## When Business Logic Must Prevent Underflow

Transfers and withdrawals must not directly store `FHE.sub(balance, amount)`. Compare first, then select:

```solidity
ebool canSpend = FHE.ge(balance, amount);
euint64 next = FHE.select(canSpend, FHE.sub(balance, amount), balance);
```

Boundary test:

```solidity
function test_transfer_doesNotUnderflow(uint64 balance, uint64 amount) public {
    vm.assume(amount > balance);

    _mint(alice, balance);

    (externalEuint64 encryptedAmount, bytes memory proof) = encryptUint64(amount, alice, address(token));

    vm.prank(alice);
    token.transfer(bob, encryptedAmount, proof);

    assertEq(_userDecryptBalance(alicePk, alice), balance);
    assertEq(_userDecryptBalance(bobPk, bob), 0);
}
```

This asserts application semantics: insufficient balance does not debit the sender and does not credit the recipient.

## Bool, Comparison, and select

`ebool` is not a Solidity `bool`; it cannot be used in a normal `if`. When testing encrypted conditions, assert on the final encrypted result:

```solidity
function test_select_fuzz(uint64 balance, uint64 amount) public {
    (externalEuint64 bal, bytes memory balProof) = encryptUint64(balance, address(checker));
    (externalEuint64 amt, bytes memory amtProof) = encryptUint64(amount, address(checker));

    euint64 selected = checker.spendOrKeep(bal, balProof, amt, amtProof);

    uint64 expected = amount <= balance ? balance - amount : balance;
    assertEq(decrypt(selected), expected);
}
```

## Encrypted-Input Error Matrix

| Symptom | Typical cause |
| --- | --- |
| `FHE.fromExternal` reverts | The `encrypt*` target is not the actual contract |
| Balance is written to the wrong account | Helper binds Alice, but the transaction is not `vm.prank(alice)` |
| Multi-input proof fails | A Hardhat input-builder pattern was copied into the current Foundry helper flow |
| Result is always 0 | State was not written, a zero handle was read, or no FHE operation was emitted |

Troubleshooting:

```bash
rg "function encrypt" dependencies/forge-fhevm-*/src/FhevmTest.sol
rg "function fromExternal" dependencies/@fhevm-solidity-*/lib/FHE.sol
forge test -vvv --match-test <name>
```

## User-Decrypt Error Matrix

| Error | Check first |
| --- | --- |
| `UserAddressEqualsContractAddress()` | Whether the test set the user and contract to the same address |
| `UserNotAuthorizedForDecrypt(bytes32,address)` | Whether `FHE.allow(value, user)` was called, and whether only transient permission exists |
| `ContractNotAuthorizedForDecrypt(bytes32,address)` | Whether `FHE.allowThis(value)` was called |
| `InvalidUserDecryptSignature()` | Whether private key, user, contract list, and timestamp match |

`userDecrypt` is internal. To catch the selector, use a wrapper:

```solidity
function callUserDecrypt(bytes32 handle, address user, address contractAddress, bytes memory sig)
    external
    returns (uint256)
{
    return userDecrypt(handle, user, contractAddress, sig);
}
```

## Public-Decrypt Error Matrix

| Symptom | Check first |
| --- | --- |
| `HandleNotAllowedForPublicDecryption(bytes32)` | Whether the application contract called `FHE.makePubliclyDecryptable` |
| KMS signature verification fails | Whether handle order, ABI encoding, and proof match |
| Callback can be consumed repeatedly | Whether finalize records request/finalized state |
| Wrong result can still finalize | Whether expected handles hash or request id is bound |

The proof from `publicDecrypt(handles)` matches `abi.encode(cleartexts)`, where `cleartexts` is a `uint256[]`. If the contract verifies `abi.encode(clear0, clear1)`, use `buildDecryptionProof(handles, encoded)`.

## ACL/FHE Operation Errors

Common sources:

- Using a handle created by another sender in an FHE operation.
- Passing a forged or nonexistent `bytes32` handle.
- Incompatible types on both sides of an encrypted-encrypted operation.
- Forgetting `FHE.allowTransient` before a cross-contract call.
- Authorizing only the old handle and not reauthorizing the new handle.

Project tests do not need to copy the low-level executor tests from `forge-fhevm`, but they should cover the failure paths exposed by the application.

## HCU Depth

Upstream `FhevmTest` provides:

```solidity
disableHCUDepthLimit();
```

This only relaxes the sequential HCU depth cap while preserving total per-transaction HCU accounting. Use it only when the test orchestration is deeper than a production single-call flow, and explain the reason in the test name or a comment.

## ERC7984 / Confidential Token Helper

For the full ERC7984 token test path, see `erc7984.md`. Upstream `FhevmTest` also provides:

```solidity
dealConfidential(wrapper, user, amount);
```

It assigns wrapper underlying tokens to the user and calls `wrap`, acting like `deal` for confidential wrapper tests. Use it only when the project uses the OpenZeppelin confidential ERC7984 wrapper; standard vault/counter tests do not need it.

## Minimal Checklist

- Encrypted-input success path.
- Correctness of direct-decrypt computation results.
- User-decrypt success path.
- Failure paths for wrong users or missing ACL.
- Public-decrypt paths before and after marking.
- Overflow/underflow or boundary values.
- Zero/uninitialized handle.
- Cross-contract transient ACL.
