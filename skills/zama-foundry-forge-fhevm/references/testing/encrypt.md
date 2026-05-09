# Testing Encrypted Input

Encrypted-input tests answer one question:

```text
Can the external handle and input proof generated in the test be consumed correctly by the application contract's FHE.fromExternal call?
```

Use `FhevmTest.encrypt*` in standard tests. Do not handwrite proofs unless you truly need the low-level capabilities in `../api/input-proof-helper.md`.

## Choose the Helper First

| Plaintext value | Helper | Contract parameter |
| --- | --- | --- |
| `bool` | `encryptBool` | `externalEbool` |
| `uint8` | `encryptUint8` | `externalEuint8` |
| `uint16` | `encryptUint16` | `externalEuint16` |
| `uint32` | `encryptUint32` | `externalEuint32` |
| `uint64` | `encryptUint64` | `externalEuint64` |
| `uint128` | `encryptUint128` | `externalEuint128` |
| `uint256` | `encryptUint256` | `externalEuint256` |
| `address` | `encryptAddress` | `externalEaddress` |

Every helper returns:

```solidity
(externalE*, bytes memory inputProof)
```

## Which Overload to Use

The default user is the test contract:

```solidity
(externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(vault));
vault.deposit(amount, proof);
```

This is suitable for minimal unit tests.

An explicit user is closer to a real transaction:

```solidity
uint256 alicePk = 0xA11CE;
address alice = vm.addr(alicePk);

(externalEuint64 amount, bytes memory proof) = encryptUint64(100, alice, address(vault));

vm.prank(alice);
vault.deposit(amount, proof);
```

Use this form for user flows, multi-user balances, and ACL tests.

## Minimal Success Test

```solidity
function test_deposit_acceptsEncryptedInput() public {
    (externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(vault));

    vault.deposit(amount, proof);

    assertEq(decrypt(vault.balanceOf(address(this))), 100);
}
```

This test proves:

- `encryptUint64` generated a verifiable input proof.
- `target = address(vault)` matches the contract that calls `FHE.fromExternal`.
- The FHE computation result is recorded by the `forge-fhevm` plaintext tracker.

It does not prove:

- That real users such as Alice/Bob can decrypt.
- That ACL is complete.
- That the public-decrypt flow is correct.

Cover those in `decrypt.md` and `acl.md`.

## Target Binding Is the Easiest Mistake

The input proof binds the target contract. The target must be the contract that calls `FHE.fromExternal`.

Wrong example:

```solidity
(externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(otherVault));
vault.deposit(amount, proof); // should fail
```

Test:

```solidity
function test_deposit_revertsWhenProofTargetsAnotherContract() public {
    ConfidentialVault otherVault = new ConfidentialVault();
    (externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(otherVault));

    vm.expectRevert();
    vault.deposit(amount, proof);
}
```

Do not rush to hardcode a revert selector. Different `InputVerifier` / executor versions may throw different low-level errors unless the project has pinned and confirmed the exact version.

## User Binding Must Also Match

If the input belongs to Alice, the transaction should simulate Alice as well:

```solidity
(externalEuint64 amount, bytes memory proof) = encryptUint64(222, alice, address(vault));

vm.prank(alice);
vault.deposit(amount, proof);
```

Common mistake:

```solidity
(externalEuint64 amount, bytes memory proof) = encryptUint64(222, alice, address(vault));
vault.deposit(amount, proof); // msg.sender is the test contract, not alice
```

Some application contracts use `msg.sender` as the balance owner or authorization subject. In that case, a user/proof and sender mismatch makes the test cover the wrong account.

## Multiple Encrypted Inputs

Currently, `FhevmTest.encrypt*` is a convenient layer that generates one handle/proof at a time. The simplest contract interface gives each external input its own proof:

```solidity
function setPair(
    externalEuint64 encryptedA,
    bytes calldata proofA,
    externalEuint64 encryptedB,
    bytes calldata proofB
) external {
    euint64 a = FHE.fromExternal(encryptedA, proofA);
    euint64 b = FHE.fromExternal(encryptedB, proofB);
    euint64 sum = FHE.add(a, b);

    _sum = sum;
    FHE.allowThis(sum);
    FHE.allow(sum, msg.sender);
}
```

Test:

```solidity
function test_setPair() public {
    (externalEuint64 a, bytes memory proofA) = encryptUint64(40, address(pair));
    (externalEuint64 b, bytes memory proofB) = encryptUint64(2, address(pair));

    pair.setPair(a, proofA, b, proofB);

    assertEq(decrypt(pair.sum()), 42);
}
```

If the project needs multiple handles to share one proof, read `../api/input-proof-helper.md` and assemble it manually against the current source.

## Direct Proof Verification Is Only for Debugging

Usually, you do not need to call `_executor.verifyInput` directly. The contract's `FHE.fromExternal` follows the same path.

For proof debugging:

```solidity
import {FheType} from "@fhevm/host-contracts/contracts/shared/FheType.sol";

function test_encryptUint64_proofVerifiable() public {
    (externalEuint64 handle, bytes memory proof) = encryptUint64(42, address(this));

    bytes32 verified = _executor.verifyInput(
        externalEuint64.unwrap(handle),
        address(this),
        proof,
        FheType.Uint64
    );

    assertEq(verified, externalEuint64.unwrap(handle));
}
```

## Checklist

- `target` is the contract that actually calls `FHE.fromExternal`.
- Multi-user tests use the three-argument overload.
- `vm.prank(user)` matches the sender expected by the application logic.
- Contract parameters use `externalE*`; do not skip `FHE.fromExternal` by passing raw `bytes32`.
- Do not use `FHE.asEuintXX(clearUserInput)` for private user input.
- Do not copy Hardhat's `createEncryptedInput` API into multi-input Foundry tests.
