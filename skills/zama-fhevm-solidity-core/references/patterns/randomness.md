# 开发模式：Encrypted Randomness

## 适用场景

使用 `FHE.randE*` 生成链上 encrypted random value，适合：

- 隐私游戏随机状态
- 抽签或匹配
- sealed game round
- 需要先保密、后续 user/public decrypt 的随机结果

## 基本用法

```solidity
ebool coin = FHE.randEbool();
euint8 die = FHE.randEuint8(8);
euint16 number = FHE.randEuint16();
```

常用函数：

- `FHE.randEbool()`
- `FHE.randEuint8()` / `FHE.randEuint8(upperBound)`
- `FHE.randEuint16()` / `FHE.randEuint16(upperBound)`
- `FHE.randEuint32()` / `FHE.randEuint32(upperBound)`
- `FHE.randEuint64()` / `FHE.randEuint64(upperBound)`
- `FHE.randEuint128()` / `FHE.randEuint128(upperBound)`
- `FHE.randEuint256()` / `FHE.randEuint256(upperBound)`

## 交易限制

随机数生成需要更新链上 PRNG 状态，必须在 transaction 中执行，不能依赖 `eth_call`。

```solidity
function roll() external {
    euint8 value = FHE.randEuint8(8);
    _rolls[msg.sender] = value;
    FHE.allowThis(value);
    FHE.allow(value, msg.sender);
}
```

不要把随机函数放在只读 `view` getter 里。

## Bounded random

bounded random 的 upper bound 应为 2 的幂，结果范围是 `[0, upperBound - 1]`：

```solidity
euint8 r = FHE.randEuint8(32); // 0..31
```

如果业务需要 1..6 的骰子，不要直接用 `upperBound = 6`。可用 8 作为上界，再设计 rejection/映射逻辑；但 rejection 不能泄露或基于 encrypted condition break loop。更简单做法是接受 0..7 并把游戏规则定义为 8 面骰。

## ACL

随机值也是新 handle，必须授权：

```solidity
_secret = FHE.randEuint32();
FHE.allowThis(_secret);
FHE.allow(_secret, msg.sender);
```

如果未来公开揭示：

```solidity
FHE.makePubliclyDecryptable(_secret);
```

## Commit/reveal 类游戏

常见结构：

1. transaction 中生成 encrypted random。
2. 用 `FHE.select` 或比较完成 encrypted game logic。
3. 保存 encrypted result 并授权合约。
4. 到结算阶段 public decrypt 必要结果，验证 proof 后执行公开奖励。

## 安全和成本

- 每次 random 都消耗 gas/HCU。
- 不要在循环里大量生成 random，除非成本可接受。
- 不要在同一函数里生成 random 后立即 public decrypt 期望同步得到结果；public decrypt 是异步流程。
