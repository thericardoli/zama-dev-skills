# UserDecryptHelper API

`UserDecryptHelper` 是 `signUserDecrypt` 背后的 EIP-712 digest 工具。普通测试不要直接用它；优先用：

```solidity
bytes memory sig = signUserDecrypt(userPk, address(vault));
uint256 clear = userDecrypt(handle, user, address(vault), sig);
```

只有在需要手动核验签名、对齐前端签名参数、或测试 user decrypt typed data 时，才直接使用本 helper。

## Mental model

user decrypt 签名证明的是：

```text
某个用户允许在某段时间内，
为某些 contract addresses 发起 user decrypt 请求。
```

它不证明 handle 已授权。handle 权限来自 ACL：

```solidity
FHE.allowThis(value);
FHE.allow(value, user);
```

所以 user decrypt 测试总是两部分：

1. 合约业务逻辑正确设置 ACL。
2. 用户签名和 decrypt request 参数一致。

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

构造 EIP-712 domain：

```text
name = "Decryption"
version = "1"
chainId = chainId
verifyingContract = verifyingContract
```

在 `FhevmTest.signUserDecrypt` 中，`verifyingContract` 是 `kmsVerifierAdd`。

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

参数说明：

| 参数 | `FhevmTest` 默认做法 | 含义 |
| --- | --- | --- |
| `publicKey` | `abi.encodePacked(userAddress)` | user decrypt 请求里的用户标识 |
| `contractAddresses` | 单合约或多合约数组 | 签名允许哪些合约参与解密 |
| `startTimestamp` | `block.timestamp` | 签名有效期开始 |
| `durationDays` | `1` | 有效天数 |
| `extraData` | `hex"00"` | 额外签名数据 |
| `domainSeparator` | Decryption domain | KMSVerifier domain |

## signUserDecrypt 内部等价逻辑

简单重载：

```solidity
bytes memory sig = signUserDecrypt(userPk, address(vault));
```

等价于：

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

完整重载内部大致是：

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

## userDecrypt 会检查什么

`userDecrypt(handle, user, contractAddress, signature)` 不只是验签。它还检查 ACL：

- user 不能等于 contract address。
- user 必须对 handle 有 persistent ACL。
- contract 必须对 handle 有 persistent ACL。
- signature 必须 recover 到 user。

因此这些失败代表不同问题：

| 错误 | 先查什么 |
| --- | --- |
| `UserNotAuthorizedForDecrypt` | 是否调用 `FHE.allow(value, user)` |
| `ContractNotAuthorizedForDecrypt` | 是否调用 `FHE.allowThis(value)` |
| `InvalidUserDecryptSignature` | pk、contract list、timestamp、duration、domain 是否一致 |
| `UserAddressEqualsContractAddress` | 测试地址是否误用了同一个地址 |

## 常见错误

- 只生成了 signature，却忘记合约里设置 ACL。
- 用 Bob 的 private key 签名，然后把 Alice 传给 `userDecrypt`。
- 签名 contract list 里是 `vaultA`，但 `userDecrypt` 传的是 `vaultB`。
- 用多合约签名时，测试和前端对 `contractAddresses` 顺序或内容不一致。
- 用当前 block timestamp 签名后，在测试里 `vm.warp`，导致手动 digest 校验和预期不一致。
