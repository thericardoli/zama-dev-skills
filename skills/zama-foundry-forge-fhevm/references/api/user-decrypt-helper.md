# UserDecryptHelper API

`UserDecryptHelper` is the EIP-712 digest utility behind `signUserDecrypt`. Standard tests should prefer:

```solidity
bytes memory sig = signUserDecrypt(userPk, address(vault));
uint256 clear = userDecrypt(handle, user, address(vault), sig);
```

Use this helper directly only when you need to manually verify signatures, align frontend signing parameters, or test user-decrypt typed data.

## Mental Model

A user-decrypt signature proves:

```text
A user permits user-decrypt requests
for specific contract addresses during a specific time window.
```

It does not prove that a handle is authorized. Handle permissions come from ACL:

```solidity
FHE.allowThis(value);
FHE.allow(value, user);
```

Therefore user-decrypt tests always have two parts:

1. Contract business logic sets ACL correctly.
2. The user signature matches the decrypt request parameters.

## Import

```solidity
import {UserDecryptHelper} from "forge-fhevm/UserDecryptHelper.sol";
import {kmsVerifierAdd} from "@fhevm/host-contracts/addresses/FHEVMHostAddresses.sol";
```

## computeUserDecryptDomainSeparator

```solidity
function computeUserDecryptDomainSeparator(
    uint256 chainId,
    address verifyingContract
) internal pure returns (bytes32);
```

Builds the EIP-712 domain:

```text
name = "Decryption"
version = "1"
chainId = chainId
verifyingContract = verifyingContract
```

In `FhevmTest.signUserDecrypt`, `verifyingContract` is `kmsVerifierAdd`.

## computeUserDecryptDigest

```solidity
function computeUserDecryptDigest(
    bytes memory publicKey,
    address[] memory contractAddresses,
    uint256 startTimestamp,
    uint256 durationDays,
    bytes memory extraData,
    bytes32 domainSeparator
) internal pure returns (bytes32);
```

Parameters:

| Parameter | `FhevmTest` default | Meaning |
| --- | --- | --- |
| `publicKey` | `abi.encodePacked(userAddress)` | User identifier in the user-decrypt request |
| `contractAddresses` | Single-contract or multi-contract array | Contracts the signature authorizes for decryption |
| `startTimestamp` | `block.timestamp` | Start of the signature validity window |
| `durationDays` | `1` | Validity duration in days |
| `extraData` | `hex"00"` | Additional signed data |
| `domainSeparator` | Decryption domain | KMSVerifier domain |

## Internal Equivalent of signUserDecrypt

Simple overload:

```solidity
bytes memory sig = signUserDecrypt(userPk, address(vault));
```

Equivalent to:

```solidity
address[] memory contracts = new address[](1);
contracts[0] = address(vault);

bytes memory sig = signUserDecrypt(
    userPk,
    contracts,
    block.timestamp,
    DEFAULT_USER_DECRYPT_DURATION_DAYS
);
```

The full overload is roughly:

```solidity
address userAddress = vm.addr(userPk);
bytes32 domain = UserDecryptHelper.computeUserDecryptDomainSeparator(block.chainid, kmsVerifierAdd);
bytes32 digest = UserDecryptHelper.computeUserDecryptDigest(
    abi.encodePacked(userAddress),
    contractAddresses,
    startTimestamp,
    durationDays,
    EMPTY_EXTRA_DATA,
    domain
);

(uint8 v, bytes32 r, bytes32 s) = vm.sign(userPk, digest);
bytes memory signature = abi.encodePacked(r, s, v);
```

## What userDecrypt Checks

`userDecrypt(handle, user, contractAddress, signature)` does more than verify the signature. It also checks ACL:

- The user must not equal the contract address.
- The user must have persistent ACL on the handle.
- The contract must have persistent ACL on the handle.
- The signature must recover to the user.

These failures indicate different problems:

| Error | Check first |
| --- | --- |
| `UserNotAuthorizedForDecrypt` | Whether `FHE.allow(value, user)` was called |
| `ContractNotAuthorizedForDecrypt` | Whether `FHE.allowThis(value)` was called |
| `InvalidUserDecryptSignature` | Whether pk, contract list, timestamp, duration, and domain all match |
| `UserAddressEqualsContractAddress` | Whether the test accidentally reused the same address |

## Common Errors

- Generating only the signature but forgetting to set ACL in the contract.
- Signing with Bob's private key, then passing Alice to `userDecrypt`.
- Signing a contract list that contains `vaultA`, then passing `vaultB` to `userDecrypt`.
- Using a multi-contract signature while the test and frontend disagree on the order or contents of `contractAddresses`.
- Signing with the current block timestamp, then calling `vm.warp` in the test, which makes a manually checked digest differ from expectations.
