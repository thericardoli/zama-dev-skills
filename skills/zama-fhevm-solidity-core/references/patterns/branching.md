# 开发模式：Branching、Loops 与 Error Handling

## 核心限制

encrypted comparison 返回 `ebool`。`ebool` 不能驱动 Solidity 的 `if`、`while`、`require` 或 `revert`，因为那会要求链上知道明文条件。

错误写法：

```solidity
ebool canTransfer = FHE.ge(balance, amount);
if (canTransfer) {
    // invalid
}
```

正确方向：

- 在 encrypted domain 内用 `FHE.select` 做条件更新。
- 如果必须进入普通 Solidity 分支，先通过 public decrypt 走异步 finalize。

## FHE.select 条件赋值

```solidity
ebool isAbove = FHE.lt(highestBid, bid);
highestBid = FHE.select(isAbove, bid, highestBid);
winningAddress = FHE.select(isAbove, FHE.asEaddress(msg.sender), winningAddress);

FHE.allowThis(highestBid);
FHE.allowThis(winningAddress);
```

`FHE.select(condition, valueIfTrue, valueIfFalse)` 会生成新的 encrypted handle。即使明文结果等于旧值，也要重新考虑 ACL。

## Fail-closed 业务更新

余额不足时不 revert，而是把更新量设为 0：

```solidity
function _transfer(address from, address to, euint64 amount) internal {
    ebool canTransfer = FHE.ge(_balances[from], amount);
    euint64 moved = FHE.select(canTransfer, amount, FHE.asEuint64(0));

    _balances[from] = FHE.sub(_balances[from], moved);
    _balances[to] = FHE.add(_balances[to], moved);

    FHE.allowThis(_balances[from]);
    FHE.allowThis(_balances[to]);
    FHE.allow(_balances[from], from);
    FHE.allow(_balances[to], to);
}
```

如果用户需要知道失败原因，配合 encrypted error code。

## Encrypted error code

encrypted 条件失败不会自动 revert。可以为每个用户记录最近错误：

```solidity
struct LastError {
    euint8 code;
    uint256 timestamp;
}

euint8 internal NO_ERROR;
euint8 internal NOT_ENOUGH_FUNDS;
mapping(address => LastError) private _lastErrors;

event ErrorChanged(address indexed user);

constructor() {
    NO_ERROR = FHE.asEuint8(0);
    NOT_ENOUGH_FUNDS = FHE.asEuint8(1);
    FHE.allowThis(NO_ERROR);
    FHE.allowThis(NOT_ENOUGH_FUNDS);
}

function _setLastError(address user, euint8 code) internal {
    _lastErrors[user] = LastError(code, block.timestamp);
    FHE.allowThis(code);
    FHE.allow(code, user);
    emit ErrorChanged(user);
}
```

在业务逻辑中：

```solidity
ebool ok = FHE.ge(balance, amount);
_setLastError(msg.sender, FHE.select(ok, NO_ERROR, NOT_ENOUGH_FUNDS));
```

encrypted 常量如果会在后续交易中复用，也需要在初始化时给合约自身持久权限。

前端监听 `ErrorChanged`，读取 handle 后 user decrypt。

## 固定轮数循环

不能用 encrypted condition break loop：

```solidity
while (FHE.lt(x, maxValue)) {
    // invalid
}
```

改成公开上界的固定轮数循环：

```solidity
for (uint256 i = 0; i < 10; i++) {
    euint8 shouldAdd = FHE.select(FHE.lt(x, maxValue), FHE.asEuint8(2), FHE.asEuint8(0));
    x = FHE.add(x, shouldAdd);
}
```

固定轮数上界必须可接受 gas/HCU 成本。若上界很大，重新设计产品逻辑。

## 避免 encrypted index

用 encrypted index 从数组中选择元素通常很贵，因为为了隐藏 index，需要遍历所有元素并用 `FHE.select` 聚合：

```solidity
euint32 selected = FHE.asEuint32(0);
for (uint256 i = 0; i < items.length; i++) {
    ebool matchIndex = FHE.eq(encryptedIndex, FHE.asEuint32(uint32(i)));
    selected = FHE.select(matchIndex, items[i], selected);
}
```

除非数组很小，否则避免这种模式。

## 异步公开分支

如果普通 Solidity 逻辑必须依赖 encrypted result，例如“赢家领取 NFT”，流程应拆成：

1. encrypted 逻辑计算 `winningAddress`。
2. auction end 后 `makePubliclyDecryptable(winningAddress)` 并 emit request。
3. off-chain public decrypt。
4. `finalize` 验证 proof，写入公开 `winnerAddress`。
5. 后续普通 `require(msg.sender == winnerAddress)` 分支。

这就是 sealed-bid auction 类应用的基本结构。
