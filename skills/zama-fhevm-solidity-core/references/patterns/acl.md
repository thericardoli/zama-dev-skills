# 开发模式：ACL 权限控制

## ACL 的基本问题

FHEVM 中 encrypted handle 不是谁拿到 `bytes32` 都能使用。ACL 控制：

- 哪个合约能继续计算某个 handle
- 哪个用户能 user decrypt 某个 handle
- 某个 handle 是否可以 public decrypt
- 某个临时调用路径是否能使用 handle

没有 ACL 权限时，即使合约持有 handle，也不能在未来交易中继续操作它。因此每次生成新 ciphertext 后，都要重新思考权限传播。

## 基本授权组合

保存状态后通常至少：

```solidity
_balance[user] = nextBalance;
FHE.allowThis(nextBalance);
FHE.allow(nextBalance, user);
```

如果返回值只在同一笔交易里传给另一个合约，可用 transient：

```solidity
FHE.allowTransient(value, target);
```

如果结果要公开：

```solidity
FHE.makePubliclyDecryptable(result);
```

## 链式语法

如果项目启用 `using FHE for *;`，可以使用链式授权：

```solidity
using FHE for *;

_value = FHE.add(_value, amount);
_value.allowThis().allow(msg.sender);
```

链式写法只是语法糖。团队风格不统一时，优先使用显式 `FHE.allow...`，降低误读风险。

## 多用户转账模式

```solidity
function transfer(address to, externalEuint64 encryptedAmount, bytes calldata proof) external {
    euint64 amount = FHE.fromExternal(encryptedAmount, proof);

    euint64 senderBalance = _balances[msg.sender];
    euint64 recipientBalance = _balances[to];

    ebool canTransfer = FHE.ge(senderBalance, amount);
    euint64 nextSender = FHE.select(canTransfer, FHE.sub(senderBalance, amount), senderBalance);
    euint64 nextRecipient = FHE.select(canTransfer, FHE.add(recipientBalance, amount), recipientBalance);

    _balances[msg.sender] = nextSender;
    _balances[to] = nextRecipient;

    FHE.allowThis(nextSender);
    FHE.allowThis(nextRecipient);
    FHE.allow(nextSender, msg.sender);
    FHE.allow(nextRecipient, to);
}
```

注意：如果 sender 也需要知道 recipient 更新是否成功，需要额外授权或设计事件/公开状态。

## 输入 handle 的 sender 授权检查

如果函数接收的 encrypted handle 不是本次 `FHE.fromExternal` 产生，而是来自现有状态或其他合约传入，应检查调用者是否有权使用该 handle：

```solidity
function consumeExisting(euint64 amount) external {
    if (!FHE.isSenderAllowed(amount)) {
        revert UnauthorizedHandle();
    }
    // safe to use amount under current ACL assumptions
}
```

这类检查可以减少通过观察交易成功/失败推断他人隐私状态的攻击面。

## 检查权限

```solidity
if (!FHE.isSenderAllowed(value)) {
    revert Unauthorized();
}

bool aliceAllowed = FHE.isAllowed(value, alice);
```

`isSenderAllowed` 适合保护“调用者必须已经有权使用这个 handle”的函数。

## Cross-contract transient 授权

把 encrypted value 传给另一个合约本次调用使用时：

```solidity
FHE.allowTransient(amount, address(token));
token.confidentialTransferFrom(msg.sender, address(this), amount);
```

常见于 ERC7984、auction、AMM、vesting、wrapper 等组合合约。不要给外部合约永久权限，除非它确实需要跨交易使用该 handle。

## 权限传播策略

设计每个状态变量时回答：

- 谁需要继续参与链上计算？
- 谁需要 user decrypt？
- 是否允许 public decrypt？
- recipient、spender、delegate、operator 是否需要权限？
- 旧 handle 权限是否可以接受？

## 高价值 secret 和 reorg

如果某个 handle 一旦授权给错误用户会造成不可逆高价值损失，例如私钥、密钥材料、重大拍卖结果，应使用两阶段授权：先记录购买或资格状态，等待足够区块确认后再调用 `FHE.allow`。详见 `reorgs.md`。

## 常见错误

- 更新状态后只 `allow(user)`，忘记 `allowThis`。
- 给了 owner 全局 decrypt 权限，但产品并不允许 owner 看用户隐私值。
- transfer 后 recipient 无法 decrypt 自己余额。
- public decrypt 被当作“方便调试”留在生产代码。
- 把 transient authorization 用作长期权限。
- 外部合约调用前忘记 `allowTransient`，导致 ERC7984 或组合合约内部操作失败。
