# InputProofHelper API

`InputProofHelper` is the low-level utility behind the `encrypt*` helpers. Standard tests should not use it directly; open this file only when `FhevmTest.encryptUint64(value, user, target)` is not enough.

Typical reasons to use it directly:

- A single input proof must contain multiple handles.
- You need control over `extraData`.
- You need to test `InputVerifier` itself.
- You need to match frontend/SDK input-proof encoding exactly.

If you only need to pass an encrypted amount to a contract function, use `FhevmTest.encryptUint64`.

## Mental Model

An input proof proves:

```text
These handles were signed by an input signer,
and this user is allowed to submit them to this contract on this chain.
```

The digest therefore binds:

- handles
- user address
- target contract address
- chain id
- extra data
- InputVerifier domain

If the target or user is wrong, `FHE.fromExternal` should fail.

## Import

```solidity
import {InputProofHelper} from "forge-fhevm/InputProofHelper.sol";
import {FheType} from "@fhevm/host-contracts/contracts/shared/FheType.sol";
```

Common addresses:

```solidity
import {aclAdd, inputVerifierAdd} from "@fhevm/host-contracts/addresses/FHEVMHostAddresses.sol";
```

## Most Common Low-Level Flow

This is essentially a simplified version of `FhevmTest._encrypt`:

```solidity
bytes memory ciphertext = abi.encodePacked(keccak256(abi.encodePacked(value, uint8(FheType.Uint64), nonce)));

bytes32 handle = InputProofHelper.computeInputHandle(
    ciphertext,
    0,
    FheType.Uint64,
    aclAdd,
    uint64(block.chainid)
);

bytes32[] memory handles = new bytes32[](1);
handles[0] = handle;

bytes32 domain = InputProofHelper.computeInputVerifierDomainSeparator(inputVerifierAdd, block.chainid);
bytes32 digest = InputProofHelper.computeInputVerificationDigest(
    handles,
    user,
    target,
    block.chainid,
    hex"00",
    domain
);

bytes[] memory signatures = new bytes[](1);
signatures[0] = _signDigest(MOCK_INPUT_SIGNER_PK, digest);

bytes memory proof = InputProofHelper.assembleInputProof(handles, signatures, hex"00");
```

For normal application tests, `encrypt*` performs all of this for you.

## computeInputHandle

```solidity
function computeInputHandle(
    bytes memory mockCiphertext,
    uint8 index,
    FheType fheType,
    address aclAddress,
    uint64 chainId
) internal pure returns (bytes32 handle);
```

It compresses a mock ciphertext and context into an FHEVM handle. The handle encodes:

- `index`: the handle's position in the proof.
- `chainId`: the target chain.
- `fheType`: `Bool`, `Uint8`, `Uint64`, and so on.
- `HANDLE_VERSION`.

Notes:

- Single-handle proofs use `index = 0`.
- In multi-handle proofs, each handle should have a distinct index, matching the handle order in the proof.
- `fheType` must match the external type passed to `FHE.fromExternal`.

## computeInputVerifierDomainSeparator

```solidity
function computeInputVerifierDomainSeparator(
    address verifyingContract,
    uint256 chainId
) internal pure returns (bytes32);
```

Builds the EIP-712 domain:

```text
name = "InputVerification"
version = "1"
chainId = chainId
verifyingContract = verifyingContract
```

In `FhevmTest`, `verifyingContract` is `inputVerifierAdd`.

## computeInputVerificationDigest

```solidity
function computeInputVerificationDigest(
    bytes32[] memory handles,
    address userAddress,
    address contractAddress,
    uint256 contractChainId,
    bytes memory extraData,
    bytes32 domainSeparator
) internal pure returns (bytes32);
```

This digest is what the input signer signs.

How to choose parameters:

| Parameter | Usual value | What happens if it is wrong |
| --- | --- | --- |
| `handles` | All input handles in the proof | Proof and handle no longer match |
| `userAddress` | User initiating the encrypted input | User binding fails |
| `contractAddress` | Contract that calls `FHE.fromExternal` | Target binding fails |
| `contractChainId` | `block.chainid` | Chain binding fails |
| `extraData` | Usually `hex"00"` | Digest mismatch |
| `domainSeparator` | Input verifier domain | Signer domain mismatch |

## assembleInputProof

```solidity
function assembleInputProof(
    bytes32[] memory handles,
    bytes[] memory signatures,
    bytes memory extraData
) internal pure returns (bytes memory proof);
```

Wire format:

```text
[handleCount:1][sigCount:1][handles...][signatures...][extraData]
```

Each signature is 65 bytes:

```text
r || s || v
```

## Common Errors

- Setting `target` to the test contract address instead of the application contract address.
- `userAddress` not matching `vm.prank(user)`.
- In multi-handle proofs, mismatching indexes, handle order, or contract parameter semantics.
- `contractChainId` not matching the domain chain id.
- Manually constructing a proof but forgetting to insert the plaintext into the test plaintext database. Standard tests should avoid this and use `encrypt*`.
