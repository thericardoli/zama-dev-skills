# KMSDecryptionProofHelper API

`KMSDecryptionProofHelper` 是 public decrypt proof 背后的底层工具。普通测试优先用：

- `publicDecrypt(handles)`：同时读取 cleartexts，并检查 public decrypt flag。
- `buildDecryptionProof(handles, abiEncodedCleartexts)`：只生成指定编码的 proof。

只有当你要手动构造 KMS proof 或测试 `KMSVerifier` 本身时，才直接用本 helper。

## Mental model

KMS proof 证明的是：

```text
这些 encrypted handles 对应这一段 ABI-encoded cleartext bytes。
```

所以 digest 绑定的是：

- handles list
- `decryptedResult` bytes
- extra data
- KMSVerifier domain

它不表达“业务上是否允许公开”。public decrypt 权限、request id、防重放，要由合约逻辑和测试单独覆盖。

## Import

```solidity
import {KMSDecryptionProofHelper} from "forge-fhevm/KMSDecryptionProofHelper.sol";
```

## 两种常见编码

`publicDecrypt(handles)` 使用：

```solidity
abi.encode(cleartexts)
```

其中 `cleartexts` 是 `uint256[]`。

自定义 callback 常常使用业务编码：

```solidity
abi.encode(winner, amount)
```

这两种编码不等价。合约用哪一种验证，proof 就必须按哪一种生成。

## computeKMSDecryptionDomainSeparator

```solidity
function computeKMSDecryptionDomainSeparator(
    string memory name,
    string memory version,
    uint256 chainId,
    address verifyingContract
) internal pure returns (bytes32);
```

通常不要手写 `name` / `version`，而是从当前 `_kmsVerifier.eip712Domain()` 读取：

```solidity
(, string memory name, string memory version, uint256 chainId, address verifyingContract,,) =
    _kmsVerifier.eip712Domain();
```

然后计算 domain separator。

## computeDecryptionDigest

```solidity
function computeDecryptionDigest(
    bytes32[] memory handlesList,
    bytes memory decryptedResult,
    bytes memory extraData,
    bytes32 domainSeparator
) internal pure returns (bytes32);
```

参数说明：

| 参数 | 含义 |
| --- | --- |
| `handlesList` | 被解密的 handle 列表，顺序必须稳定 |
| `decryptedResult` | ABI-encoded cleartext bytes |
| `extraData` | 默认通常是 `hex"00"` |
| `domainSeparator` | 当前 KMSVerifier 的 EIP-712 domain |

如果 handles 顺序变了、`decryptedResult` 编码变了，原 proof 就不再有效。

## assembleDecryptionProof

```solidity
function assembleDecryptionProof(
    bytes[] memory signatures,
    bytes memory extraData
) internal pure returns (bytes memory proof);
```

wire format：

```text
[sigCount:1][signatures...][extraData]
```

每个签名是 65 bytes：

```text
r || s || v
```

`FhevmTest` 默认只用一个 mock KMS signer。

## 什么时候用 publicDecrypt，什么时候用 buildDecryptionProof

用 `publicDecrypt`：

```solidity
(uint256[] memory cleartexts, bytes memory proof) = publicDecrypt(handles);
contract.verify(handles, abi.encode(cleartexts), proof);
```

前提：合约验证的就是 `abi.encode(uint256[])`。

用 `buildDecryptionProof`：

```solidity
bytes memory encoded = abi.encode(winner, amount);
bytes memory proof = buildDecryptionProof(handles, encoded);
contract.finalize(handles, encoded, proof);
```

前提：合约验证的是自定义业务编码。

## 常见错误

- 用 `publicDecrypt` 得到 proof，却在合约里按 `abi.encode(clear0, clear1)` 验证。
- handles 顺序和 cleartext 编码顺序不一致。
- 只验证了 KMS proof，却没测试 request id、expected handles、deadline、replay protection。
- 把 `buildDecryptionProof` 当成 public decrypt 权限检查；它不检查 ACL。
