# Fuzz、边界和常见错误

Fuzz 测试不要只随机跑成功路径。对 FHEVM 合约，fuzz 最有价值的是覆盖：

- 定宽整数 wrapping。
- encrypted comparison + `FHE.select` 的边界。
- zero/uninitialized handle。
- 错 user、错 target、错 ACL。
- public/user decrypt 的失败路径。

## Wrapping 是什么

`euint8`、`euint16`、`euint64` 这类 FHE 整数有固定 bit 宽度。结果超出范围时，语义通常和同宽度无符号整数一样按模数回绕。

例子：

```text
euint8: 255 + 1 = 0
euint8: 250 + 10 = 4
euint8: 0 - 1 = 255
```

所以测试 `euint64` 加法时，expected 也要按 `uint64` 语义算：

```solidity
uint64 expected;
unchecked {
    expected = a + b;
}
```

余额、额度、供应量通常不希望业务上发生 wrapping。合约要用 encrypted comparison 和 `FHE.select` 让失败路径保持原状态。

## 算术 fuzz

适合测试纯 FHE 运算 helper：

```solidity
function test_add_fuzz(uint64 a, uint64 b) public {
    (externalEuint64 left, bytes memory leftProof) = encryptUint64(a, address(adder));
    (externalEuint64 right, bytes memory rightProof) = encryptUint64(b, address(adder));

    euint64 sum = adder.add(left, leftProof, right, rightProof);

    uint64 expected;
    unchecked {
        expected = a + b;
    }

    assertEq(decrypt(sum), expected);
}
```

这个测试承认 wrapping 是底层运算语义的一部分。

## 业务不允许 underflow 时

转账、提款这类业务不能直接保存 `FHE.sub(balance, amount)`。先比较，再 select：

```solidity
ebool canSpend = FHE.ge(balance, amount);
euint64 next = FHE.select(canSpend, FHE.sub(balance, amount), balance);
```

测试边界：

```solidity
function test_transfer_doesNotUnderflow(uint64 balance, uint64 amount) public {
    vm.assume(amount > balance);

    _mint(alice, balance);

    (externalEuint64 encryptedAmount, bytes memory proof) = encryptUint64(amount, alice, address(token));

    vm.prank(alice);
    token.transfer(bob, encryptedAmount, proof);

    assertEq(_userDecryptBalance(alicePk, alice), balance);
    assertEq(_userDecryptBalance(bobPk, bob), 0);
}
```

这里断言的是业务语义：余额不足时不扣款、不给 recipient 增加余额。

## Bool、比较和 select

`ebool` 不是 Solidity `bool`，不能拿来写普通 `if`。测试 encrypted 条件时，检查最终 encrypted result：

```solidity
function test_select_fuzz(uint64 balance, uint64 amount) public {
    (externalEuint64 bal, bytes memory balProof) = encryptUint64(balance, address(checker));
    (externalEuint64 amt, bytes memory amtProof) = encryptUint64(amount, address(checker));

    euint64 selected = checker.spendOrKeep(bal, balProof, amt, amtProof);

    uint64 expected = amount <= balance ? balance - amount : balance;
    assertEq(decrypt(selected), expected);
}
```

## Encrypted input 错误矩阵

| 现象 | 典型原因 |
| --- | --- |
| `FHE.fromExternal` revert | `encrypt*` 的 target 不是实际合约 |
| 余额写到错误账户 | helper 绑定了 Alice，但交易不是 `vm.prank(alice)` |
| 多输入 proof 失败 | 把 Hardhat input builder 模式搬到当前 Foundry helper |
| 结果一直是 0 | 没写状态、读了 zero handle，或没有触发 FHE operation |

排查：

```bash
rg "function encrypt" dependencies/forge-fhevm-*/src/FhevmTest.sol
rg "function fromExternal" dependencies/@fhevm-solidity-*/lib/FHE.sol
forge test -vvv --match-test <name>
```

## User decrypt 错误矩阵

| 错误 | 先查什么 |
| --- | --- |
| `UserAddressEqualsContractAddress()` | 测试是否把 user 和 contract 设成同一地址 |
| `UserNotAuthorizedForDecrypt(bytes32,address)` | 是否调用 `FHE.allow(value, user)`，是否只有 transient |
| `ContractNotAuthorizedForDecrypt(bytes32,address)` | 是否调用 `FHE.allowThis(value)` |
| `InvalidUserDecryptSignature()` | private key、user、contract list、timestamp 是否匹配 |

`userDecrypt` 是 internal。要捕捉 selector，用 wrapper：

```solidity
function callUserDecrypt(bytes32 handle, address user, address contractAddress, bytes memory sig)
    external
    returns (uint256)
{
    return userDecrypt(handle, user, contractAddress, sig);
}
```

## Public decrypt 错误矩阵

| 现象 | 先查什么 |
| --- | --- |
| `HandleNotAllowedForPublicDecryption(bytes32)` | 业务合约是否调用 `FHE.makePubliclyDecryptable` |
| KMS signature 验证失败 | handles 顺序、ABI 编码、proof 是否匹配 |
| callback 可重复消费 | finalize 是否记录 request/finalized 状态 |
| 错结果也能 finalize | 是否绑定 expected handles hash 或 request id |

`publicDecrypt(handles)` 的 proof 匹配 `abi.encode(cleartexts)`，其中 `cleartexts` 是 `uint256[]`。如果合约验证的是 `abi.encode(clear0, clear1)`，用 `buildDecryptionProof(handles, encoded)`。

## ACL/FHE 运算错误

常见来源：

- 用其他 sender 创建的 handle 做 FHE 运算。
- 传入伪造或不存在的 `bytes32` handle。
- enc-enc 运算两侧类型不兼容。
- 跨合约调用前忘记 `FHE.allowTransient`。
- 只给旧 handle 授权，新 handle 没有重新授权。

项目测试不必复制 `forge-fhevm` 的 executor 底层测试，但业务暴露出的失败路径要覆盖。

## HCU 深度

上游 `FhevmTest` 提供：

```solidity
disableHCUDepthLimit();
```

它只放宽 sequential HCU depth cap，保留 total per-transaction HCU accounting。仅在测试编排比生产单次调用更深时使用，并在测试名或注释中说明原因。

## ERC7984 / confidential token 辅助

ERC7984 token 的完整测试路径见 `erc7984.md`。上游 `FhevmTest` 还提供：

```solidity
dealConfidential(wrapper, user, amount);
```

它给 user 分配 wrapper underlying token 并调用 `wrap`，相当于 confidential wrapper 测试里的 `deal`。只在项目使用 OpenZeppelin confidential ERC7984 wrapper 时使用；普通 vault/counter 测试不需要。

## 最小检查清单

- encrypted input 成功路径。
- direct decrypt 的计算正确性。
- user decrypt 成功路径。
- 错误用户或缺 ACL 的失败路径。
- public decrypt 标记前后路径。
- overflow/underflow 或边界值。
- zero/uninitialized handle。
- 跨合约 transient ACL。
