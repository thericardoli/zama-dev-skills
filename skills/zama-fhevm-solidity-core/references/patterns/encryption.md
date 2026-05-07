# 开发模式：加密输入

## 适用场景

当合约函数需要接收用户隐私输入时，使用 external encrypted input 模式。典型场景包括：

- confidential token mint/transfer amount
- 私密投票选择
- sealed-bid auction 出价
- 隐私游戏操作
- 用户提交的私密阈值、地址、布尔开关

## 两种 encrypted value 来源

FHEVM 合约里常见两种 encrypted value 来源：

1. **链下用户输入加密**：客户端在链下生成 `externalEuintXX` 和 `inputProof`，合约用 `FHE.fromExternal` 验证。具体生成方式取决于前端 SDK、Hardhat 或 Foundry skill。
2. **链上 trusted value 转换**：合约用 `FHE.asEuintXX(clear)` 把可信明文常量或部署参数转成 encrypted value。

用户输入必须走第一种。不要用 `FHE.asEuintXX` 接收不可信用户输入。

## 合约侧接收加密输入

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {FHE, euint32, externalEuint32} from "@fhevm/solidity/lib/FHE.sol";
import {ZamaEthereumConfig} from "@fhevm/solidity/config/ZamaConfig.sol";

contract ConfidentialCounter is ZamaEthereumConfig {
    euint32 private _count;

    function increment(externalEuint32 encryptedAmount, bytes calldata inputProof) external {
        euint32 amount = FHE.fromExternal(encryptedAmount, inputProof);

        _count = FHE.add(_count, amount);

        FHE.allowThis(_count);
        FHE.allow(_count, msg.sender);
    }

    function getCount() external view returns (euint32) {
        return _count;
    }
}
```

要点：

- `externalEuint32` 是外部 handle 参数，不是内部可直接计算的 `euint32`。
- `inputProof` 可以覆盖同一笔交易中多个 encrypted input。
- `FHE.fromExternal` 是验证边界。所有用户输入都应在这里进入 encrypted domain。
- 验证后的 `amount` 可以传入 `FHE.add`、`FHE.sub`、`FHE.select` 等 API。

## 多个 encrypted input

多个输入可以打包进同一个 ciphertext/proof。合约侧可以接收多个 `externalE*`，最后共用一个 `bytes inputProof`：

```solidity
function initialize(
    externalEbool inputFlag,
    externalEuint32 inputAmount,
    externalEaddress inputOwner,
    bytes calldata inputProof
) external {
    ebool flag = FHE.fromExternal(inputFlag, inputProof);
    euint32 amount = FHE.fromExternal(inputAmount, inputProof);
    eaddress owner = FHE.fromExternal(inputOwner, inputProof);

    _flag = flag;
    _amount = amount;
    _owner = owner;

    FHE.allowThis(_flag);
    FHE.allowThis(_amount);
    FHE.allowThis(_owner);
    FHE.allow(_flag, msg.sender);
    FHE.allow(_amount, msg.sender);
    FHE.allow(_owner, msg.sender);
}
```

客户端必须保持 handles 与 Solidity 参数的语义对应。文档说明 Solidity 参数顺序不要求和构造输入顺序固定一致，但实际开发中应保持一致，减少错配风险。

框架侧生成 encrypted input 的具体写法放在对应 skill：

- Hardhat：`zama-hardhat-contract-dev`
- Foundry/forge-fhevm：`zama-foundry-forge-fhevm`
- React/wagmi/viem、Node 脚本或低层 SDK：`zama-sdk`

## Trusted value 转换

适合初始供应量、管理员配置、常量：

```solidity
euint64 initial = FHE.asEuint64(1_000);
FHE.allowThis(initial);
FHE.allow(initial, owner);
```

不适合：

```solidity
function deposit(uint64 clearAmount) external {
    euint64 amount = FHE.asEuint64(clearAmount); // 用户明文输入，隐私已泄露
}
```

原因：trivial encryption 只是把明文变成 FHE 操作兼容的 ciphertext 形式，明文已经在 calldata 或合约状态变化中公开，不提供输入隐私。

## 初始化检查

状态变量默认是 zero handle。需要区分“未初始化”和“明文值为 0”时，使用：

```solidity
if (!FHE.isInitialized(_count)) {
    // first write path
}
```

不要把 `euintXX.unwrap(value) == 0` 写进业务代码；优先使用 `FHE.isInitialized`。

## 常见错误

- 加密时绑定了 contract A，调用时传给 contract B。
- 加密时绑定了 alice，交易由 bob 发出。
- 合约参数写成 `bytes32`，跳过了 `FHE.fromExternal`。
- 状态更新后忘记 `FHE.allowThis`。
- 使用 `FHE.asEuintXX(userInput)` 接收本应保密的用户输入。
