# FhevmTest API

`FhevmTest` is the primary entry point for Foundry FHEVM tests. It does three things:

1. Deploys the FHEVM host contracts inside the Forge test environment.
2. Uses mock signers to generate input proofs, KMS proofs, and user-decrypt signatures.
3. Tracks the plaintext behind encrypted handles so tests can assert on results.

## Minimal Working Template

```solidity
import {FhevmTest} from "forge-fhevm/FhevmTest.sol";
import {FHE, euint64, externalEuint64} from "@fhevm/solidity/lib/FHE.sol";
import {ZamaEthereumConfig} from "@fhevm/solidity/config/ZamaConfig.sol";

contract Vault is ZamaEthereumConfig {
    euint64 private _balance;

    function deposit(externalEuint64 encryptedAmount, bytes calldata proof) external {
        euint64 amount = FHE.fromExternal(encryptedAmount, proof);
        _balance = FHE.add(_balance, amount);
        FHE.allowThis(_balance);
        FHE.allow(_balance, msg.sender);
    }

    function balance() external view returns (euint64) {
        return _balance;
    }
}

contract VaultTest is FhevmTest {
    Vault vault;

    function setUp() public override {
        super.setUp();
        vault = new Vault();
    }

    function test_deposit() public {
        (externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(vault));
        vault.deposit(amount, proof);
        assertEq(decrypt(vault.balance()), 100);
    }
}
```

`super.setUp()` is essential; without it, the FHEVM host contracts are not available in the test environment.

## Helper Selection Table

| What you want to test | Helper to use | Does it check ACL? |
| --- | --- | --- |
| Convert plaintext test values into encrypted input | `encryptBool` / `encryptUintXX` / `encryptAddress` | The input proof binds the user and target |
| Quickly assert encrypted computation results | `decrypt` | No |
| Public decrypt request/callback flows | `publicDecrypt` | Checks the public-decrypt flag |
| Custom callback proof encoding | `buildDecryptionProof` | No |
| A user reading an authorized handle | `signUserDecrypt` + `userDecrypt` | Checks persistent ACL and signature |
| ERC7984 wrapper initial balances | `dealConfidential` | Not applicable |
| Test orchestration that exceeds the HCU depth cap | `disableHCUDepthLimit` | Not applicable |

## setUp

```solidity
function setUp() public virtual;
```

`FhevmTest.setUp()`:

- Sets `block.chainid = 31337`.
- Deploys `FHEVMExecutor`, `ACL`, `InputVerifier`, and `KMSVerifier`.
- Configures mock input and KMS signers.
- Starts log recording so the plaintext tracker can observe FHE operation events.

Call it first when overriding:

```solidity
function setUp() public override {
    super.setUp();
    // deploy contracts under test
}
```

## Encryption Helpers

Every `encrypt*` helper returns:

```solidity
(externalE*, bytes memory inputProof)
```

Two-argument overload:

```solidity
(externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(vault));
```

Meaning:

- value: `100`
- user: `address(this)`
- target: `address(vault)`

The three-argument overload is better for simulating real users:

```solidity
uint256 alicePk = 0xA11CE;
address alice = vm.addr(alicePk);

(externalEuint64 amount, bytes memory proof) = encryptUint64(100, alice, address(vault));

vm.prank(alice);
vault.deposit(amount, proof);
```

Supported types:

| Helper | Plaintext type | External handle |
| --- | --- | --- |
| `encryptBool` | `bool` | `externalEbool` |
| `encryptUint8` | `uint8` | `externalEuint8` |
| `encryptUint16` | `uint16` | `externalEuint16` |
| `encryptUint32` | `uint32` | `externalEuint32` |
| `encryptUint64` | `uint64` | `externalEuint64` |
| `encryptUint128` | `uint128` | `externalEuint128` |
| `encryptUint256` | `uint256` | `externalEuint256` |
| `encryptAddress` | `address` | `externalEaddress` |

Signatures:

```solidity
function encryptUint64(uint64 value, address target) internal returns (externalEuint64, bytes memory);
function encryptUint64(uint64 value, address user, address target) internal returns (externalEuint64, bytes memory);
```

Other types follow the same two-argument and three-argument overload pattern.

Notes:

- `target` must be the contract that actually calls `FHE.fromExternal`.
- Prefer the three-argument overload for multi-user tests.
- Every encryption increments the nonce, so encrypting the same value twice still produces different handles.

## Direct Decrypt

```solidity
function decrypt(euint64 value) internal returns (uint64);
function decrypt(bytes32 handle) internal returns (uint256);
```

`decrypt` is a test assertion tool. It does not check `FHE.allow`, `FHE.allowThis`, the public-decrypt flag, or user signatures.

Good use:

```solidity
assertEq(decrypt(vault.balance()), 100);
```

It does not prove:

- That a user can really decrypt in the product.
- That the handle has been authorized correctly.
- That a public-decrypt callback is safe.

Typed overloads:

```solidity
function decrypt(ebool value) internal returns (bool);
function decrypt(euint8 value) internal returns (uint8);
function decrypt(euint16 value) internal returns (uint16);
function decrypt(euint32 value) internal returns (uint32);
function decrypt(euint64 value) internal returns (uint64);
function decrypt(euint128 value) internal returns (uint128);
function decrypt(euint256 value) internal returns (uint256);
function decrypt(eaddress value) internal returns (address);
```

## Public Decrypt

```solidity
function publicDecrypt(bytes32[] memory handles)
    internal
    returns (uint256[] memory cleartexts, bytes memory decryptionProof);
```

Use `publicDecrypt` to test that a result is allowed to be public and that the KMS proof can be verified by the contract.

Application contracts usually mark the value first:

```solidity
FHE.makePubliclyDecryptable(result);
```

Test:

```solidity
bytes32[] memory handles = new bytes32[](1);
handles[0] = euint64.unwrap(vault.balance());

(uint256[] memory cleartexts, bytes memory proof) = publicDecrypt(handles);
vault.verifyPublicDecrypt(handles, abi.encode(cleartexts), proof);
```

Behavior:

- Every handle must already be marked as public decryptable in the ACL.
- Returned `cleartexts` are ordered the same way as `handles`.
- The proof is generated for `abi.encode(cleartexts)`.

When a handle has not been marked:

```solidity
HandleNotAllowedForPublicDecryption(handle)
```

If the contract callback expects `abi.encode(clear0, clear1)` instead of `abi.encode(uint256[])`, do not use the proof returned by `publicDecrypt`; use `buildDecryptionProof` instead.

## buildDecryptionProof

```solidity
function buildDecryptionProof(bytes32[] memory handles, bytes memory abiEncodedCleartexts)
    internal
    view
    returns (bytes memory proof);

function buildDecryptionProof(bytes32 handle, bytes memory abiEncodedCleartext)
    internal
    view
    returns (bytes memory proof);
```

It does exactly one thing: generate a mock KMS proof for the handles and encoded cleartexts you provide.

It does not:

- Check the public-decrypt flag.
- Check a request id.
- Check whether a callback can be consumed more than once.
- Check whether the cleartext is authorized by application logic.

Use it for custom finalize tests:

```solidity
bytes32 handle = euint64.unwrap(vault.balance());
uint64 clear = decrypt(vault.balance());
bytes memory encoded = abi.encode(clear);
bytes memory proof = buildDecryptionProof(handle, encoded);

vault.finalize(handle, encoded, proof);
```

## User Decrypt

User decrypt has two steps:

```solidity
bytes memory sig = signUserDecrypt(userPk, address(vault));
uint256 clear = userDecrypt(handle, user, address(vault), sig);
```

Signature helper:

```solidity
function signUserDecrypt(uint256 userPk, address contractAddress)
    internal
    view
    returns (bytes memory signature);

function signUserDecrypt(
    uint256 userPk,
    address[] memory contractAddresses,
    uint256 startTimestamp,
    uint256 durationDays
) internal view returns (bytes memory signature);
```

Decryption helper:

```solidity
function userDecrypt(
    bytes32 handle,
    address userAddress,
    address contractAddress,
    bytes memory userSignature
) internal returns (uint256);
```

`userDecrypt` checks:

- `userAddress != contractAddress`
- The user has persistent ACL on the handle
- The contract has persistent ACL on the handle
- The signature recovers to `userAddress`

Therefore the contract side usually needs:

```solidity
FHE.allowThis(value);
FHE.allow(value, user);
```

Common errors:

| Error | Usual cause |
| --- | --- |
| `UserNotAuthorizedForDecrypt` | Missing `FHE.allow(value, user)` |
| `ContractNotAuthorizedForDecrypt` | Missing `FHE.allowThis(value)` |
| `InvalidUserDecryptSignature` | Signature key, contract list, time parameters, or user do not match |
| `UserAddressEqualsContractAddress` | User address equals contract address |

## ERC7984/HCU Helpers

```solidity
function dealConfidential(IERC7984ERC20Wrapper wrapper, address user, uint256 amount) internal;
```

The confidential-token version of `deal`: it gives the user underlying tokens, approves the wrapper, then wraps them into confidential tokens.

```solidity
function disableHCUDepthLimit() internal;
```

This only relaxes the sequential HCU depth cap. Use it only when the test orchestration is deeper than a production single-call flow, and document the reason in the test.

## Internal State and Constants

These are primarily for low-level debugging; standard application tests rarely need them:

```solidity
FHEVMExecutor internal _executor;
ACL internal _acl;
InputVerifier internal _inputVerifier;
KMSVerifier internal _kmsVerifier;

address internal mockInputSigner;
address internal mockKmsSigner;
```

Current source constants:

```solidity
uint256 internal constant MOCK_INPUT_SIGNER_PK =
    0x7ec8ada6642fc4ccfb7729bc29c17cf8d21b61abd5642d1db992c0b8672ab901;
uint256 internal constant MOCK_KMS_SIGNER_PK =
    0x388b7680e4e1afa06efbfd45cdd1fe39f3c6af381df6555a19661f283b97de91;

bytes internal constant EMPTY_EXTRA_DATA = hex"00";
uint256 internal constant DEFAULT_USER_DECRYPT_DURATION_DAYS = 1;
```
