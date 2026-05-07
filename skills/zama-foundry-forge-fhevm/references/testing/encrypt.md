# 测试 encrypted input

encrypted input 测试回答一个问题：

```text
测试里生成的 external handle + input proof，是否能被业务合约的 FHE.fromExternal 正确消费？
```

普通测试用 `FhevmTest.encrypt*`。不要手写 proof，除非你真的需要 `../api/input-proof-helper.md` 里的底层能力。

## 先选 helper

| 明文值 | Helper | 合约参数 |
| --- | --- | --- |
| `bool` | `encryptBool` | `externalEbool` |
| `uint8` | `encryptUint8` | `externalEuint8` |
| `uint16` | `encryptUint16` | `externalEuint16` |
| `uint32` | `encryptUint32` | `externalEuint32` |
| `uint64` | `encryptUint64` | `externalEuint64` |
| `uint128` | `encryptUint128` | `externalEuint128` |
| `uint256` | `encryptUint256` | `externalEuint256` |
| `address` | `encryptAddress` | `externalEaddress` |

每个 helper 都返回：

```solidity
(externalE*, bytes memory inputProof)
```

## 两种重载怎么选

默认 user 是测试合约：

```solidity
(externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(vault));
vault.deposit(amount, proof);
```

这适合最小单元测试。

显式 user 更接近真实交易：

```solidity
uint256 alicePk = 0xA11CE;
address alice = vm.addr(alicePk);

(externalEuint64 amount, bytes memory proof) = encryptUint64(100, alice, address(vault));

vm.prank(alice);
vault.deposit(amount, proof);
```

这适合用户流程、多用户余额、ACL 测试。

## 最小成功测试

```solidity
function test_deposit_acceptsEncryptedInput() public {
    (externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(vault));

    vault.deposit(amount, proof);

    assertEq(decrypt(vault.balanceOf(address(this))), 100);
}
```

这个测试证明：

- `encryptUint64` 生成了可验证 input proof。
- `target = address(vault)` 和 `FHE.fromExternal` 的调用合约一致。
- FHE 运算结果能被 `forge-fhevm` plaintext tracker 记录。

它没有证明：

- Alice/Bob 这类真实用户能 decrypt。
- ACL 设置完整。
- public decrypt 流程正确。

这些要在 `decrypt.md` 和 `acl.md` 里补。

## target 绑定最容易写错

input proof 绑定了 target contract。target 必须是调用 `FHE.fromExternal` 的那个合约。

错误示例：

```solidity
(externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(otherVault));
vault.deposit(amount, proof); // 应失败
```

测试：

```solidity
function test_deposit_revertsWhenProofTargetsAnotherContract() public {
    ConfidentialVault otherVault = new ConfidentialVault();
    (externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(otherVault));

    vm.expectRevert();
    vault.deposit(amount, proof);
}
```

不要急着写死 revert selector。不同版本的 `InputVerifier` / executor 可能抛出不同底层错误，除非项目已经固定并确认。

## user 绑定也要一致

如果 input 是 Alice 的，交易也应模拟 Alice：

```solidity
(externalEuint64 amount, bytes memory proof) = encryptUint64(222, alice, address(vault));

vm.prank(alice);
vault.deposit(amount, proof);
```

常见误写：

```solidity
(externalEuint64 amount, bytes memory proof) = encryptUint64(222, alice, address(vault));
vault.deposit(amount, proof); // msg.sender 是测试合约，不是 alice
```

有些业务合约会把 `msg.sender` 作为余额 owner 或授权对象；这时 user/proof 和 sender 错位会让测试覆盖到错误账户。

## 多个 encrypted inputs

当前 `FhevmTest.encrypt*` 是“一次生成一个 handle/proof”的易用层。最简单的合约接口是每个 external input 带自己的 proof：

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

测试：

```solidity
function test_setPair() public {
    (externalEuint64 a, bytes memory proofA) = encryptUint64(40, address(pair));
    (externalEuint64 b, bytes memory proofB) = encryptUint64(2, address(pair));

    pair.setPair(a, proofA, b, proofB);

    assertEq(decrypt(pair.sum()), 42);
}
```

如果项目需要“多个 handles 共用一个 proof”，再读 `../api/input-proof-helper.md`，按当前源码手动组装。

## 直接验证 proof 只用于排错

通常不需要直接调 `_executor.verifyInput`。业务合约里的 `FHE.fromExternal` 会走同一条路径。

排查 proof 时可以这样：

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

- `target` 是实际调用 `FHE.fromExternal` 的合约。
- 多用户测试使用三参数重载。
- `vm.prank(user)` 和业务预期的 sender 一致。
- 合约参数使用 `externalE*`，不要用裸 `bytes32` 跳过 `FHE.fromExternal`。
- 用户隐私输入不要用 `FHE.asEuintXX(clearUserInput)`。
- 多输入测试不要照搬 Hardhat 的 `createEncryptedInput` API。
