# 开发模式：Encrypted Operations

## 适用场景

当任务涉及 encrypted arithmetic、比较、位运算、类型转换、overflow 控制或 gas/HCU 优化时，读取本文件。

## 类型选择

优先选择能覆盖业务范围的最小 encrypted type：

- 小范围枚举、百分比、等级：`euint8`
- 计数器、小额积分：`euint32` 或 `euint64`
- token amount：常见为 `euint64`，以协议或库要求为准
- 大整数、密钥材料：`euint128` 或 `euint256`
- 隐私地址：`eaddress`
- 隐私条件：`ebool`

不要默认使用 `euint256`。encrypted 操作成本高，类型越大越贵。

## 算术

常用：

```solidity
euint64 c = FHE.add(a, b);
euint64 d = FHE.sub(a, b);
euint64 e = FHE.mul(a, b);
euint64 q = FHE.div(a, 10);
euint64 r = FHE.rem(a, 10);
```

注意：

- `div` 和 `rem` 的 rhs 通常应为明文 scalar。
- encrypted integer arithmetic 是 unchecked，overflow/underflow 不会像 Solidity 0.8 普通整数那样自动 revert。
- 合约不能直接从 encrypted comparison 得到普通 `bool` 来 revert。

## Scalar 优先

同样逻辑下，能用明文 scalar 就不要先 trivial encrypt：

```solidity
// 较差：多一次 encrypted value 构造
x = FHE.add(x, FHE.asEuint32(42));

// 较好：使用 scalar 重载
x = FHE.add(x, 42);
```

前提是 scalar 本身不需要保密。

## Overflow-safe mint/update

encrypted total supply 或余额更新时，使用比较和 `FHE.select` 做 fail-closed 更新：

```solidity
function mint(externalEuint32 encryptedAmount, bytes calldata inputProof) external {
    euint32 amount = FHE.fromExternal(encryptedAmount, inputProof);

    euint32 nextSupply = FHE.add(totalSupply, amount);
    ebool overflow = FHE.lt(nextSupply, totalSupply);

    totalSupply = FHE.select(overflow, totalSupply, nextSupply);

    euint32 nextBalance = FHE.add(balances[msg.sender], amount);
    balances[msg.sender] = FHE.select(overflow, balances[msg.sender], nextBalance);

    FHE.allowThis(totalSupply);
    FHE.allowThis(balances[msg.sender]);
    FHE.allow(balances[msg.sender], msg.sender);
}
```

这个模式不会 revert，而是在 overflow 时保持旧状态。前端可通过 encrypted error code 或 public/user decrypt 的状态给用户反馈。

## 比较与 min/max

```solidity
ebool enough = FHE.ge(balance, amount);
euint64 smaller = FHE.min(a, b);
euint64 larger = FHE.max(a, b);
```

`ebool` 是 encrypted condition，只能继续参与 FHE 运算或 `FHE.select`，不能写成：

```solidity
if (enough) {
    // invalid
}
```

## 条件更新

余额不足时保持旧余额：

```solidity
ebool canSpend = FHE.ge(balance, amount);
euint64 spend = FHE.select(canSpend, amount, FHE.asEuint64(0));

balances[from] = FHE.sub(balance, spend);
balances[to] = FHE.add(balances[to], spend);
```

## Casting 和 trivial encryption

Trusted 明文转 encrypted：

```solidity
euint64 publicAmount = FHE.asEuint64(100);
ebool flag = FHE.asEbool(true);
eaddress account = FHE.asEaddress(msg.sender);
```

类型转换：

```solidity
euint64 wide = FHE.asEuint64(narrow32);
euint32 truncated = FHE.asEuint32(wide);
```

从小到大保留信息；从大到小可能截断。trivial encryption 的明文仍是公开的，不要用于保护用户隐私输入。

## 位运算

适合 bitmap、masked flags、低层协议状态：

```solidity
euint32 masked = FHE.and(value, 0xff);
euint32 shifted = FHE.shr(value, 8);
euint32 rotated = FHE.rotl(value, 3);
```

shift/rotate 的位数可能按目标 bit width 取模。需要精确语义时查当前 `FHE.sol`。

## 授权结果

所有产生新 handle 的操作后，都要重新设置 ACL：

```solidity
result = FHE.add(a, b);
FHE.allowThis(result);
FHE.allow(result, msg.sender);
```

不要以为输入 handle 的权限会自动传播到输出 handle 的长期权限。
