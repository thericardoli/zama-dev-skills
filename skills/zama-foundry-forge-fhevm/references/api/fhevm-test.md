# FhevmTest API

`FhevmTest` 是写 Foundry FHEVM 测试时最常用的入口。它做三件事：

1. 在 Forge 测试环境里部署 FHEVM host contracts。
2. 用 mock signer 生成 input proof、KMS proof 和 user decrypt signature。
3. 跟踪 encrypted handle 对应的明文，方便测试断言。

## 最短可用模板

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

`super.setUp()` 是关键；没有它，测试环境里没有 FHEVM host contracts。

## Helper 选择表

| 你想测试什么 | 用哪个 helper | 它检查 ACL 吗 |
| --- | --- | --- |
| 把明文测试值变成 encrypted input | `encryptBool` / `encryptUintXX` / `encryptAddress` | input proof 绑定 user 和 target |
| 快速断言 encrypted 计算结果 | `decrypt` | 不检查 |
| public decrypt request/callback | `publicDecrypt` | 检查 public decrypt flag |
| 自定义 callback proof | `buildDecryptionProof` | 不检查 |
| 用户读取自己被授权的 handle | `signUserDecrypt` + `userDecrypt` | 检查 persistent ACL 和签名 |
| ERC7984 wrapper 初始余额 | `dealConfidential` | 不适用 |
| 测试编排导致 HCU 深度过深 | `disableHCUDepthLimit` | 不适用 |

## setUp

```solidity
function setUp() public virtual;
```

`FhevmTest.setUp()` 会：

- 设置 `block.chainid = 31337`。
- 部署 `FHEVMExecutor`、`ACL`、`InputVerifier`、`KMSVerifier`。
- 配置 mock input signer 和 mock KMS signer。
- 启动 log recording，让 plaintext tracker 能看到 FHE operation events。

覆写时先调用：

```solidity
function setUp() public override {
    super.setUp();
    // deploy contracts under test
}
```

## Encryption helpers

所有 `encrypt*` helper 都返回：

```solidity
(externalE*, bytes memory inputProof)
```

两参数重载：

```solidity
(externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(vault));
```

含义：

- value: `100`
- user: `address(this)`
- target: `address(vault)`

三参数重载适合模拟真实用户：

```solidity
uint256 alicePk = 0xA11CE;
address alice = vm.addr(alicePk);

(externalEuint64 amount, bytes memory proof) = encryptUint64(100, alice, address(vault));

vm.prank(alice);
vault.deposit(amount, proof);
```

支持类型：

| Helper | 明文类型 | external handle |
| --- | --- | --- |
| `encryptBool` | `bool` | `externalEbool` |
| `encryptUint8` | `uint8` | `externalEuint8` |
| `encryptUint16` | `uint16` | `externalEuint16` |
| `encryptUint32` | `uint32` | `externalEuint32` |
| `encryptUint64` | `uint64` | `externalEuint64` |
| `encryptUint128` | `uint128` | `externalEuint128` |
| `encryptUint256` | `uint256` | `externalEuint256` |
| `encryptAddress` | `address` | `externalEaddress` |

签名：

```solidity
function encryptUint64(uint64 value, address target) internal returns (externalEuint64, bytes memory);
function encryptUint64(uint64 value, address user, address target) internal returns (externalEuint64, bytes memory);
```

其他类型同样是两参数和三参数两种形式。

注意：

- `target` 必须是实际调用 `FHE.fromExternal` 的合约。
- 多用户测试优先使用三参数重载。
- 每次 encrypt 都会递增 nonce，同一个值加密两次也会得到不同 handle。

## Direct decrypt

```solidity
function decrypt(euint64 value) internal returns (uint64);
function decrypt(bytes32 handle) internal returns (uint256);
```

`decrypt` 是测试断言工具。它不会检查 `FHE.allow`、`FHE.allowThis`、public decrypt flag 或用户签名。

适合：

```solidity
assertEq(decrypt(vault.balance()), 100);
```

不适合证明：

- 用户真的能在产品里解密。
- handle 已经正确授权。
- public decrypt callback 安全。

typed overloads：

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

## Public decrypt

```solidity
function publicDecrypt(bytes32[] memory handles)
    internal
    returns (uint256[] memory cleartexts, bytes memory decryptionProof);
```

`publicDecrypt` 用来测试“结果可以公开，并且 KMS proof 能被合约验证”的流程。

业务合约通常先标记：

```solidity
FHE.makePubliclyDecryptable(result);
```

测试：

```solidity
bytes32[] memory handles = new bytes32[](1);
handles[0] = euint64.unwrap(vault.balance());

(uint256[] memory cleartexts, bytes memory proof) = publicDecrypt(handles);
vault.verifyPublicDecrypt(handles, abi.encode(cleartexts), proof);
```

行为：

- 每个 handle 必须已经被 ACL 标记为可 public decrypt。
- 返回的 `cleartexts` 与 `handles` 顺序一致。
- proof 是针对 `abi.encode(cleartexts)` 生成的。

未标记时：

```solidity
HandleNotAllowedForPublicDecryption(handle)
```

如果合约 callback 需要 `abi.encode(clear0, clear1)` 而不是 `abi.encode(uint256[])`，不要用 `publicDecrypt` 的 proof，改用 `buildDecryptionProof`。

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

它只做一件事：对你给定的 handles 和 encoded cleartexts 生成 mock KMS proof。

它不会：

- 检查 public decrypt flag。
- 检查 request id。
- 检查 callback 是否可重复消费。
- 检查 cleartext 是否来自真实业务授权。

适合测试自定义 finalize：

```solidity
bytes32 handle = euint64.unwrap(vault.balance());
uint64 clear = decrypt(vault.balance());
bytes memory encoded = abi.encode(clear);
bytes memory proof = buildDecryptionProof(handle, encoded);

vault.finalize(handle, encoded, proof);
```

## User decrypt

user decrypt 由两步组成：

```solidity
bytes memory sig = signUserDecrypt(userPk, address(vault));
uint256 clear = userDecrypt(handle, user, address(vault), sig);
```

签名 helper：

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

解密 helper：

```solidity
function userDecrypt(
    bytes32 handle,
    address userAddress,
    address contractAddress,
    bytes memory userSignature
) internal returns (uint256);
```

`userDecrypt` 会检查：

- `userAddress != contractAddress`
- user 对 handle 有 persistent ACL
- contract 对 handle 有 persistent ACL
- signature recover 到 `userAddress`

所以合约侧通常必须做：

```solidity
FHE.allowThis(value);
FHE.allow(value, user);
```

常见错误：

| 错误 | 通常原因 |
| --- | --- |
| `UserNotAuthorizedForDecrypt` | 缺少 `FHE.allow(value, user)` |
| `ContractNotAuthorizedForDecrypt` | 缺少 `FHE.allowThis(value)` |
| `InvalidUserDecryptSignature` | 签名 key、contract list、时间参数或 user 不匹配 |
| `UserAddressEqualsContractAddress` | user 地址和 contract 地址相同 |

## ERC7984/HCU helpers

```solidity
function dealConfidential(IERC7984ERC20Wrapper wrapper, address user, uint256 amount) internal;
```

confidential token 版本的 `deal`：给 user underlying token，approve wrapper，然后 wrap 成 confidential token。

```solidity
function disableHCUDepthLimit() internal;
```

只放宽 sequential HCU depth cap。仅在测试编排比生产单次调用更深时使用，并在测试里说明原因。

## 内部状态和常量

这些主要用于底层排错，普通业务测试少用：

```solidity
FHEVMExecutor internal _executor;
ACL internal _acl;
InputVerifier internal _inputVerifier;
KMSVerifier internal _kmsVerifier;

address internal mockInputSigner;
address internal mockKmsSigner;
```

当前源码常量：

```solidity
uint256 internal constant MOCK_INPUT_SIGNER_PK =
    0x7ec8ada6642fc4ccfb7729bc29c17cf8d21b61abd5642d1db992c0b8672ab901;
uint256 internal constant MOCK_KMS_SIGNER_PK =
    0x388b7680e4e1afa06efbfd45cdd1fe39f3c6af381df6555a19661f283b97de91;

bytes internal constant EMPTY_EXTRA_DATA = hex"00";
uint256 internal constant DEFAULT_USER_DECRYPT_DURATION_DAYS = 1;
```
