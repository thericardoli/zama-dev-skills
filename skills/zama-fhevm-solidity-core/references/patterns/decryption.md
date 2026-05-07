# 开发模式：解密

## 解密方式选择

FHEVM 中常见三类读取路径：

- **不解密**：继续在 encrypted domain 内计算，优先选择。
- **user decrypt**：只有被授权用户在链下看到明文。
- **public decrypt**：结果公开，任何人都可以得到明文，必要时链上验证 KMS 签名后继续执行公开业务逻辑。

默认优先 user decrypt。只有结果本来就应该公开时才用 public decrypt。

## User decrypt

user decrypt 适合用户读取自己被授权的 encrypted handle，例如余额、计数器、私人投票状态。

合约侧要求：

```solidity
FHE.allowThis(value);
FHE.allow(value, user);
```

两者都重要：

- `allowThis` 允许 dApp 合约参与 user decrypt 授权路径，也允许后续继续计算。
- `allow(value, user)` 允许指定用户解密该 handle。

示例：

```solidity
function setValue(externalEuint32 input, bytes calldata proof) external {
    euint32 value = FHE.fromExternal(input, proof);
    _value = value;
    FHE.allowThis(_value);
    FHE.allow(_value, msg.sender);
}

function valueHandle() external view returns (euint32) {
    return _value;
}
```

多值 user decrypt 时，对每个 handle 都要授权合约自身和用户：

```solidity
FHE.allowThis(_encryptedBool);
FHE.allowThis(_encryptedAmount);
FHE.allowThis(_encryptedAddress);

FHE.allow(_encryptedBool, msg.sender);
FHE.allow(_encryptedAmount, msg.sender);
FHE.allow(_encryptedAddress, msg.sender);
```

链下 user decrypt 的具体调用方式由前端 SDK、Hardhat 或 Foundry skill 负责。Solidity core 只要求合约正确保存 handle 并授予 ACL。

## User decrypt 的合约设计要点

- getter 返回 encrypted handle，不返回明文。
- 合约只给业务上有权知道该值的人 `FHE.allow`。
- 如果 recipient 需要读取收到的余额，transfer 时授权 recipient。
- 如果 operator 只需要链上临时使用，优先 `allowTransient` 而不是长期 `allow`。
- 前端要处理 zero/uninitialized handle，避免无意义 decrypt。

## Public decrypt

public decrypt 适合所有人都可以知道的结果，例如最终计票、拍卖结束后的获胜价、游戏回合公开结果。

合约侧先标记：

```solidity
FHE.makePubliclyDecryptable(result);
```

典型三步：

1. 链上运行 confidential logic，得到 encrypted result。
2. 链上调用 request 函数，把 result 标记为 publicly decryptable，并 emit handle。
3. 链下 relayer/SDK 执行 public decrypt；链上 callback/finalize 用 `FHE.checkSignatures` 验证 proof 后写入公开状态。

如果链上消费解密结果，必须验证 KMS 签名：

```solidity
bytes32[] memory handles = new bytes32[](1);
handles[0] = FHE.toBytes32(result);

FHE.checkSignatures(handles, abi.encode(cleartexts), decryptionProof);
```

实际合约应把 request id、expected handles、callback caller、是否已消费等状态绑定起来，防止 replay 和错配。

多值 public decrypt 时，handles 顺序、`abi.encode(...)` 顺序、SDK public decrypt 输入顺序必须完全一致：

```solidity
bytes32[] memory handles = new bytes32[](2);
handles[0] = FHE.toBytes32(_encryptedFoo);
handles[1] = FHE.toBytes32(_encryptedBar);

bytes memory encoded = abi.encode(clearFoo, clearBar);
FHE.checkSignatures(handles, encoded, proof);
```

顺序错了，proof 即使来自真实 KMS 也应验证失败。

## Public decrypt finalize 模板

```solidity
bool private _requested;
bool private _finalized;
eaddress private _winner;
address public winner;

event WinnerDecryptionRequested(eaddress winnerHandle);

function requestWinnerDecryption() external {
    require(!_requested, "already requested");
    _requested = true;
    FHE.makePubliclyDecryptable(_winner);
    emit WinnerDecryptionRequested(_winner);
}

function finalizeWinner(bytes memory clearResult, bytes memory proof) external {
    require(_requested, "not requested");
    require(!_finalized, "already finalized");

    bytes32[] memory handles = new bytes32[](1);
    handles[0] = FHE.toBytes32(_winner);
    FHE.checkSignatures(handles, clearResult, proof);

    winner = abi.decode(clearResult, (address));
    _finalized = true;
}
```

根据业务继续加入 caller 校验、request id、deadline、expected handle hash 等约束。

## 不需要解密的场景

优先在 encrypted domain 内完成业务逻辑：

```solidity
ebool canSpend = FHE.ge(balance, amount);
euint64 next = FHE.select(canSpend, FHE.sub(balance, amount), balance);
```

不要为了做 `if` 分支就把隐私值 public decrypt。

## 常见错误

- 忘记 `FHE.allowThis`，导致 user decrypt 失败。
- 只授权 `msg.sender`，但实际需要 recipient 解密。
- 对敏感余额或订单调用 `makePubliclyDecryptable`。
- public decrypt callback 不校验 request id 或 handles。
- 前端对 zero handle 直接发起 user decrypt。
- 多值 public decrypt 的 handle 顺序和 ABI 编码顺序不一致。
- finalize 函数没有 replay protection，重复消费同一 proof。
