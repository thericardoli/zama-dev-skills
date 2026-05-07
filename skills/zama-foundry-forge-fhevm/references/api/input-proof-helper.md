# InputProofHelper API

`InputProofHelper` 是 `encrypt*` 背后的底层工具。普通测试不要直接用它；只有当 `FhevmTest.encryptUint64(value, user, target)` 不够用时才打开本文件。

典型需要直接用它的情况：

- 一份 input proof 里要放多个 handles。
- 需要控制 `extraData`。
- 需要测试 `InputVerifier` 本身。
- 需要和前端/SDK 的 input proof encoding 对齐。

如果只是给合约函数传一个 encrypted amount，用 `FhevmTest.encryptUint64`。

## Mental model

一个 input proof 证明的是：

```text
这些 handles 是由某个 input signer 签过的，
允许某个 user 在某条 chain 上把它们交给某个 contract 消费。
```

因此 digest 里会绑定：

- handles
- user address
- target contract address
- chain id
- extra data
- InputVerifier domain

target 或 user 错了，`FHE.fromExternal` 应该失败。

## Import

```solidity
import {InputProofHelper} from "forge-fhevm/InputProofHelper.sol";
import {FheType} from "@fhevm/host-contracts/contracts/shared/FheType.sol";
```

常见地址：

```solidity
import {aclAdd, inputVerifierAdd} from "@fhevm/host-contracts/addresses/FHEVMHostAddresses.sol";
```

## 最常见的底层流程

这基本就是 `FhevmTest._encrypt` 的简化版：

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

在普通业务测试里，上面这些都由 `encrypt*` 完成。

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

它把 mock ciphertext 和上下文压成 FHEVM handle。handle 里会编码：

- `index`：这个 handle 在 proof 里的位置。
- `chainId`：目标链。
- `fheType`：`Bool`、`Uint8`、`Uint64` 等。
- `HANDLE_VERSION`。

注意：

- 单 handle proof 用 `index = 0`。
- 多 handle proof 每个 handle 的 index 应不同，并和 proof 中的 handles 顺序一致。
- `fheType` 必须和合约调用 `FHE.fromExternal` 时的 external type 对得上。

## computeInputVerifierDomainSeparator

```solidity
function computeInputVerifierDomainSeparator(
    address verifyingContract,
    uint256 chainId
) internal pure returns (bytes32);
```

构造 EIP-712 domain：

```text
name = "InputVerification"
version = "1"
chainId = chainId
verifyingContract = verifyingContract
```

在 `FhevmTest` 里，`verifyingContract` 是 `inputVerifierAdd`。

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

这个 digest 是 input signer 签名的内容。

参数怎么选：

| 参数 | 通常填什么 | 错了会怎样 |
| --- | --- | --- |
| `handles` | proof 里所有 input handles | proof 和 handle 对不上 |
| `userAddress` | 发起 encrypted input 的用户 | user 绑定失败 |
| `contractAddress` | 调用 `FHE.fromExternal` 的合约 | target 绑定失败 |
| `contractChainId` | `block.chainid` | chain 绑定失败 |
| `extraData` | 默认 `hex"00"` | digest 不一致 |
| `domainSeparator` | input verifier domain | signer domain 不一致 |

## assembleInputProof

```solidity
function assembleInputProof(
    bytes32[] memory handles,
    bytes[] memory signatures,
    bytes memory extraData
) internal pure returns (bytes memory proof);
```

wire format：

```text
[handleCount:1][sigCount:1][handles...][signatures...][extraData]
```

每个签名是 65 bytes：

```text
r || s || v
```

## 常见错误

- `target` 写成测试合约地址，而不是业务合约地址。
- `userAddress` 和 `vm.prank(user)` 不一致。
- 多 handle proof 的 index、handles 顺序、合约参数语义错位。
- `contractChainId` 和 domain chain id 不一致。
- 直接构造 proof 却忘记把 plaintext 放进测试 plaintext DB。普通测试不要手写这些，优先用 `encrypt*`。
