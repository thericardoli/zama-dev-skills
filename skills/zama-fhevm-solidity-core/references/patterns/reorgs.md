# 开发模式：Reorg 风险与两阶段 ACL

## 问题

ACL 授权事件进入区块后，会被网关/relayer 观察并传播。如果链发生 reorg，某个“已经授权”的交易可能在最终链上不存在，但授权信息可能已经造成敏感信息泄露。

大多数普通余额或低价值状态不需要额外处理。但如果 handle 保护的是高价值不可逆 secret，例如私钥、解锁码、密钥材料、重大拍卖秘密，应考虑两阶段授权。

## 不推荐的单步授权

```solidity
function buySecret() external payable {
    require(msg.value == 1 ether, "price");
    require(!isBought, "sold");
    isBought = true;
    FHE.allow(secret, msg.sender);
}
```

问题：支付和授权在同一笔交易里完成，一旦短期 reorg 造成状态回滚，secret 可能已经被错误用户解密。

## 两阶段授权

```solidity
euint256 private secret;
bool public isBought;
uint256 public blockWhenBought;
address public buyer;

function buySecret() external payable {
    require(msg.value == 1 ether, "price");
    require(!isBought, "sold");
    isBought = true;
    blockWhenBought = block.number;
    buyer = msg.sender;
}

function requestSecretAccess() external {
    require(isBought, "not bought");
    require(msg.sender == buyer, "not buyer");
    require(block.number > blockWhenBought + 95, "too early");
    FHE.allow(secret, buyer);
}
```

官方文档以 Ethereum worst-case reorg 讨论 95 slots，具体等待区块数应按目标链最终性、资产价值和 UX 取舍决定。

## 适用判断

使用两阶段 ACL，当：

- secret 一旦泄露无法撤销。
- secret 价值远大于等待带来的 UX 成本。
- 授权对象是购买者、赢家或临时获得资格的人。
- 业务可以接受二次交易。

不必默认使用，当：

- handle 是普通用户余额，错误授权影响有限或可补救。
- 用户体验优先且泄露风险低。
- 已有应用层最终性等待或后端风控。

## 测试建议

- 购买后立即 `requestSecretAccess` 应 revert。
- 等待足够区块后 buyer 可以获得 ACL。
- 非 buyer 不能请求 ACL。
- 重复请求不应产生错误状态。
