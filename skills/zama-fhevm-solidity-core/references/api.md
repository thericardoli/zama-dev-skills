# fhevm-solidity Types and API Index

Use this file to quickly locate encrypted types and `FHE` APIs that are common during development. Treat the `@fhevm/solidity/lib/FHE.sol` source installed in the current project as authoritative for exact signatures. When in doubt, query the dependency source directly:

```bash
rg "function <name>" node_modules/@fhevm/solidity/lib/FHE.sol
rg "type .* is bytes32" node_modules/encrypted-types -n
```

For Foundry projects, use remappings to find the actual paths for `@fhevm/solidity` and `encrypted-types`.

## Common Imports

```solidity
import {
    FHE,
    ebool,
    euint8,
    euint16,
    euint32,
    euint64,
    euint128,
    euint256,
    eaddress,
    externalEbool,
    externalEuint8,
    externalEuint16,
    externalEuint32,
    externalEuint64,
    externalEuint128,
    externalEuint256,
    externalEaddress
} from "@fhevm/solidity/lib/FHE.sol";

import {ZamaEthereumConfig} from "@fhevm/solidity/config/ZamaConfig.sol";
```

## Encrypted Data Types

Internal encrypted types:

- `ebool`
- `euint8`
- `euint16`
- `euint32`
- `euint64`
- `euint128`
- `euint256`
- `eaddress`

External input types:

- `externalEbool`
- `externalEuint8`
- `externalEuint16`
- `externalEuint32`
- `externalEuint64`
- `externalEuint128`
- `externalEuint256`
- `externalEaddress`

Usage rules:

- Use `e*` types for state variables, internal computed values, and returned handles.
- Use `externalE*` types for encrypted inputs submitted off-chain by users.
- `externalE*` values must be paired with `bytes inputProof` and passed through `FHE.fromExternal`.
- Handles are backed by `bytes32`, but business code must not treat an arbitrary `bytes32` as a verified encrypted value.

## Configuration Types

`ZamaEthereumConfig`：

- When a contract inherits it, the constructor calls `FHE.setCoprocessor(ZamaConfig.getEthereumCoprocessorConfig())`.
- The current configuration covers Ethereum mainnet, Sepolia, and local `31337`.
- Contracts can expose the current protocol id through `confidentialProtocolId()`.

`CoprocessorConfig`：

- `ACLAddress`
- `CoprocessorAddress`
- `KMSVerifierAddress`

Most dApps do not construct this struct manually unless they integrate with a non-official Zama deployment or a special local environment.

## Input Conversion

Convert external encrypted inputs to internal types:

- `FHE.fromExternal(externalEbool, bytes) -> ebool`
- `FHE.fromExternal(externalEuint8, bytes) -> euint8`
- `FHE.fromExternal(externalEuint16, bytes) -> euint16`
- `FHE.fromExternal(externalEuint32, bytes) -> euint32`
- `FHE.fromExternal(externalEuint64, bytes) -> euint64`
- `FHE.fromExternal(externalEuint128, bytes) -> euint128`
- `FHE.fromExternal(externalEuint256, bytes) -> euint256`
- `FHE.fromExternal(externalEaddress, bytes) -> eaddress`

Convert plaintext constants or trusted values to encrypted types:

- `FHE.asEbool(bool)`
- `FHE.asEuint8(uint8)`
- `FHE.asEuint16(uint16)`
- `FHE.asEuint32(uint32)`
- `FHE.asEuint64(uint64)`
- `FHE.asEuint128(uint128)`
- `FHE.asEuint256(uint256)`
- `FHE.asEaddress(address)`

Type conversion:

- `FHE.asEbool(euintXX)`
- `FHE.asEuintXX(ebool)`
- `FHE.asEuintXX(euintYY)`, using overloads supported by the library

Note: `asEuintXX(clear)` does not verify user input. It is only suitable for constants, deployment parameters, administrator-trusted values, or tests.

## Initialization and Handle Utilities

- `FHE.isInitialized(value) -> bool`: checks whether an encrypted handle is nonzero.
- `FHE.toBytes32(value) -> bytes32`: unwraps an encrypted type into a `bytes32` handle.
- `FHE.cleanTransientStorage()`: clears transient ACL storage. This is usually handled by the protocol or testing framework and is rarely needed in ordinary business logic.

## Arithmetic APIs

Common APIs:

- `FHE.add(a, b)`
- `FHE.sub(a, b)`
- `FHE.mul(a, b)`
- `FHE.div(a, scalar)`
- `FHE.rem(a, scalar)`

Notes:

- `add/sub/mul` support multiple `euint` widths and some scalar overloads.
- `div/rem` usually support an encrypted lhs and a plaintext scalar rhs.
- FHE integer operations may wrap. For balances, limits, supply, and similar values, combine comparisons with `FHE.select` to implement fail-closed logic.

## Comparison APIs

- `FHE.eq(a, b) -> ebool`
- `FHE.ne(a, b) -> ebool`
- `FHE.gt(a, b) -> ebool`
- `FHE.ge(a, b) -> ebool`
- `FHE.lt(a, b) -> ebool`
- `FHE.le(a, b) -> ebool`
- `FHE.min(a, b) -> euintXX`
- `FHE.max(a, b) -> euintXX`

Encrypted-encrypted overloads and some encrypted-scalar overloads are supported. `ebool` cannot be used as a Solidity `bool`.

## Boolean and Bitwise APIs

Boolean:

- `FHE.and(ebool, ebool/bool)`
- `FHE.or(ebool, ebool/bool)`
- `FHE.xor(ebool, ebool/bool)`
- `FHE.not(ebool)`

Integer bit operations:

- `FHE.and(euintXX, euintYY/scalar)`
- `FHE.or(euintXX, euintYY/scalar)`
- `FHE.xor(euintXX, euintYY/scalar)`
- `FHE.not(euintXX)`
- `FHE.shl(euintXX, euintXX/scalar)`
- `FHE.shr(euintXX, euintXX/scalar)`
- `FHE.rotl(euintXX, euintXX/scalar)`
- `FHE.rotr(euintXX, euintXX/scalar)`

## Conditional Selection

- `FHE.select(ebool control, ebool a, ebool b) -> ebool`
- `FHE.select(ebool control, euintXX a, euintXX b) -> euintXX`
- `FHE.select(ebool control, eaddress a, eaddress b) -> eaddress`

This is the core tool for encrypted conditional branching. Do not try to decode an `ebool` into a normal `bool` and branch on-chain with `if`.

## Randomness

- `FHE.randEbool()`
- `FHE.randEuint8()` / `FHE.randEuint8(uint8 upperBound)`
- `FHE.randEuint16()` / `FHE.randEuint16(uint16 upperBound)`
- `FHE.randEuint32()` / `FHE.randEuint32(uint32 upperBound)`
- `FHE.randEuint64()` / `FHE.randEuint64(uint64 upperBound)`
- `FHE.randEuint128()` / `FHE.randEuint128(uint128 upperBound)`
- `FHE.randEuint256()` / `FHE.randEuint256(uint256 upperBound)`

Before using randomness, confirm that the current network and test framework support this path, and set ACL permissions for the result.

## ACL API

Permission queries:

- `FHE.isAllowed(value, account) -> bool`
- `FHE.isSenderAllowed(value) -> bool`
- `FHE.isPubliclyDecryptable(value) -> bool`
- `FHE.isUserDecryptable(value, account, contractAddress) -> bool`
- `FHE.isAccountDenied(account) -> bool`

Permission grants:

- `FHE.allow(value, account) -> value`
- `FHE.allowThis(value) -> value`
- `FHE.allowTransient(value, account) -> value`
- `FHE.makePubliclyDecryptable(value) -> value`

`allow`, `allowThis`, `allowTransient`, and `makePubliclyDecryptable` are overloaded for `ebool/euintXX/eaddress` and return the same encrypted value, which makes chaining or assignment convenient.

## User decrypt delegation

- `FHE.delegateUserDecryption(delegate, contractAddress, expirationDate)`
- `FHE.delegateUserDecryptionWithoutExpiration(delegate, contractAddress)`
- `FHE.delegateUserDecryptions(delegate, contractAddresses, expirationDate)`
- `FHE.delegateUserDecryptionsWithoutExpiration(delegate, contractAddresses)`
- `FHE.revokeUserDecryptionDelegation(delegate, contractAddress)`
- `FHE.revokeUserDecryptionDelegations(delegate, contractAddresses)`
- `FHE.isDelegatedForUserDecryption(delegate, delegator, contractAddress) -> bool`
- `FHE.getDelegatedUserDecryptionExpirationDate(delegate, delegator, contractAddress) -> uint64`

Delegation is suitable for smart wallets, proxy decryption, or backend services that initiate decryption on a user's behalf. Do not add it by default unless the product requirement is explicit.

## Public Decrypt / KMS Verification

- `FHE.checkSignatures(handlesList, cleartexts, decryptionProof)`: verifies public decrypt results on-chain.
- `FHE.verifyDecryptionEIP712KMSSignatures(handlesList, decryptedResult, decryptionProof) -> bool`
- `FHE.isPublicDecryptionResultValid(handlesList, cleartexts, decryptionProof) -> bool`
- `FHE.eip712Domain()`
- `FHE.getThreshold()`
- `FHE.getKmsSigners()`

Public decrypt reveals data. Use it only when the business logic explicitly allows everyone to know the result.

## Address Comparison

- `FHE.eq(eaddress, eaddress/address) -> ebool`
- `FHE.ne(eaddress, eaddress/address) -> ebool`

`eaddress` is suitable for private-address scenarios, but authorization and final decryption paths must be designed carefully.

## Errors and Events

Common errors:

- `SenderNotAllowedToUseHandle(bytes32 handle, address sender)`
- `InvalidKMSSignatures()`
- `EmptyDecryptionProof()`
- `KMSSignatureThresholdNotReached(uint256 numSignatures)`
- `KMSInvalidSigner(address invalidSigner)`

Events:

- `PublicDecryptionVerified(bytes32[] handlesList, bytes abiEncodedCleartexts)`

When debugging failures, inspect the revert error first, then check ACL, proof bindings, and chain id.
