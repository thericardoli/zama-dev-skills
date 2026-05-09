# KMSDecryptionProofHelper API

`KMSDecryptionProofHelper` is the low-level utility behind public-decrypt proofs. Standard tests should prefer:

- `publicDecrypt(handles)`: reads cleartexts and checks the public-decrypt flag.
- `buildDecryptionProof(handles, abiEncodedCleartexts)`: generates only the proof for the supplied encoding.

Use this helper directly only when you need to manually construct a KMS proof or test `KMSVerifier` itself.

## Mental Model

A KMS proof proves:

```text
These encrypted handles correspond to these ABI-encoded cleartext bytes.
```

The digest therefore binds:

- handles list
- `decryptedResult` bytes
- extra data
- KMSVerifier domain

It does not express whether public disclosure is allowed by the application. Public-decrypt permission, request ids, and replay protection must be covered separately by contract logic and tests.

## Import

```solidity
import {KMSDecryptionProofHelper} from "forge-fhevm/KMSDecryptionProofHelper.sol";
```

## Two Common Encodings

`publicDecrypt(handles)` uses:

```solidity
abi.encode(cleartexts)
```

where `cleartexts` is a `uint256[]`.

Custom callbacks often use application-specific encoding:

```solidity
abi.encode(winner, amount)
```

These two encodings are not equivalent. The proof must be generated with the same encoding the contract verifies.

## computeKMSDecryptionDomainSeparator

```solidity
function computeKMSDecryptionDomainSeparator(
    string memory name,
    string memory version,
    uint256 chainId,
    address verifyingContract
) internal pure returns (bytes32);
```

Usually, do not hardcode `name` or `version`; read them from the current `_kmsVerifier.eip712Domain()`:

```solidity
(, string memory name, string memory version, uint256 chainId, address verifyingContract,,) =
    _kmsVerifier.eip712Domain();
```

Then compute the domain separator.

## computeDecryptionDigest

```solidity
function computeDecryptionDigest(
    bytes32[] memory handlesList,
    bytes memory decryptedResult,
    bytes memory extraData,
    bytes32 domainSeparator
) internal pure returns (bytes32);
```

Parameters:

| Parameter | Meaning |
| --- | --- |
| `handlesList` | Handles being decrypted; order must be stable |
| `decryptedResult` | ABI-encoded cleartext bytes |
| `extraData` | Usually `hex"00"` by default |
| `domainSeparator` | Current KMSVerifier EIP-712 domain |

If the handle order changes, or if the `decryptedResult` encoding changes, the original proof is no longer valid.

## assembleDecryptionProof

```solidity
function assembleDecryptionProof(
    bytes[] memory signatures,
    bytes memory extraData
) internal pure returns (bytes memory proof);
```

Wire format:

```text
[sigCount:1][signatures...][extraData]
```

Each signature is 65 bytes:

```text
r || s || v
```

`FhevmTest` uses one mock KMS signer by default.

## When to Use publicDecrypt vs buildDecryptionProof

Use `publicDecrypt`:

```solidity
(uint256[] memory cleartexts, bytes memory proof) = publicDecrypt(handles);
contract.verify(handles, abi.encode(cleartexts), proof);
```

Prerequisite: the contract verifies `abi.encode(uint256[])`.

Use `buildDecryptionProof`:

```solidity
bytes memory encoded = abi.encode(winner, amount);
bytes memory proof = buildDecryptionProof(handles, encoded);
contract.finalize(handles, encoded, proof);
```

Prerequisite: the contract verifies custom application encoding.

## Common Errors

- Using a proof returned by `publicDecrypt` while the contract verifies `abi.encode(clear0, clear1)`.
- Mismatching the handle order and cleartext encoding order.
- Verifying only the KMS proof without testing request id, expected handles, deadline, or replay protection.
- Treating `buildDecryptionProof` as a public-decrypt permission check; it does not check ACL.
