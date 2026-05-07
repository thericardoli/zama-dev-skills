# fhevm-solidity 类型与 API 索引

本文件用于快速定位开发中常用的 encrypted 类型和 `FHE` API。具体签名以当前项目安装的 `@fhevm/solidity/lib/FHE.sol` 为准；不确定时直接在依赖源码中查询：

```bash
rg "function <name>" node_modules/@fhevm/solidity/lib/FHE.sol
rg "type .* is bytes32" node_modules/encrypted-types -n
```

Foundry 项目则按 remapping 查询 `@fhevm/solidity` 和 `encrypted-types` 的实际路径。

## 常用 import

```solidity
import {
    FHE,
    ebool,
    euint8,
    euint16,
    euint32,
    euint64,
    euint128,
    euint256,
    eaddress,
    externalEbool,
    externalEuint8,
    externalEuint16,
    externalEuint32,
    externalEuint64,
    externalEuint128,
    externalEuint256,
    externalEaddress
} from "@fhevm/solidity/lib/FHE.sol";

import {ZamaEthereumConfig} from "@fhevm/solidity/config/ZamaConfig.sol";
```

## Encrypted 数据类型

内部 encrypted 类型：

- `ebool`
- `euint8`
- `euint16`
- `euint32`
- `euint64`
- `euint128`
- `euint256`
- `eaddress`

外部输入类型：

- `externalEbool`
- `externalEuint8`
- `externalEuint16`
- `externalEuint32`
- `externalEuint64`
- `externalEuint128`
- `externalEuint256`
- `externalEaddress`

使用规则：

- 状态变量、内部计算值、返回 handle 使用 `e*` 类型。
- 用户从链下提交的 encrypted input 使用 `externalE*` 类型。
- `externalE*` 必须配合 `bytes inputProof` 并通过 `FHE.fromExternal`。
- handle 底层是 `bytes32`，但业务代码不要把任意 `bytes32` 当成已验证 encrypted value。

## 配置类型

`ZamaEthereumConfig`：

- 合约继承它后，constructor 会调用 `FHE.setCoprocessor(ZamaConfig.getEthereumCoprocessorConfig())`。
- 当前配置覆盖 Ethereum mainnet、Sepolia 和本地 `31337`。
- 合约可以通过 `confidentialProtocolId()` 暴露当前 protocol id。

`CoprocessorConfig`：

- `ACLAddress`
- `CoprocessorAddress`
- `KMSVerifierAddress`

普通 dApp 通常不手动构造该 struct，除非接入非 Zama 官方部署或特殊本地环境。

## 输入转换

外部 encrypted input 转内部类型：

- `FHE.fromExternal(externalEbool, bytes) -> ebool`
- `FHE.fromExternal(externalEuint8, bytes) -> euint8`
- `FHE.fromExternal(externalEuint16, bytes) -> euint16`
- `FHE.fromExternal(externalEuint32, bytes) -> euint32`
- `FHE.fromExternal(externalEuint64, bytes) -> euint64`
- `FHE.fromExternal(externalEuint128, bytes) -> euint128`
- `FHE.fromExternal(externalEuint256, bytes) -> euint256`
- `FHE.fromExternal(externalEaddress, bytes) -> eaddress`

明文常量或 trusted value 转 encrypted type：

- `FHE.asEbool(bool)`
- `FHE.asEuint8(uint8)`
- `FHE.asEuint16(uint16)`
- `FHE.asEuint32(uint32)`
- `FHE.asEuint64(uint64)`
- `FHE.asEuint128(uint128)`
- `FHE.asEuint256(uint256)`
- `FHE.asEaddress(address)`

类型转换：

- `FHE.asEbool(euintXX)`
- `FHE.asEuintXX(ebool)`
- `FHE.asEuintXX(euintYY)`，按库支持的重载使用

注意：`asEuintXX(clear)` 不验证用户输入，只适合常量、部署参数、管理员可信值或测试。

## 初始化和 handle 工具

- `FHE.isInitialized(value) -> bool`：检查 encrypted handle 是否非零。
- `FHE.toBytes32(value) -> bytes32`：把 encrypted type unwrap 成 `bytes32` handle。
- `FHE.cleanTransientStorage()`：清理 transient ACL 存储，通常由协议或测试框架处理，普通业务少用。

## 算术 API

常用：

- `FHE.add(a, b)`
- `FHE.sub(a, b)`
- `FHE.mul(a, b)`
- `FHE.div(a, scalar)`
- `FHE.rem(a, scalar)`

说明：

- `add/sub/mul` 支持多种 `euint` 宽度和部分 scalar 重载。
- `div/rem` 通常只支持 encrypted lhs 与明文 scalar rhs。
- FHE 整数运算可能有 wrapping 行为。余额、额度、供应量等场景要配合比较和 `FHE.select` 做 fail-closed 逻辑。

## 比较 API

- `FHE.eq(a, b) -> ebool`
- `FHE.ne(a, b) -> ebool`
- `FHE.gt(a, b) -> ebool`
- `FHE.ge(a, b) -> ebool`
- `FHE.lt(a, b) -> ebool`
- `FHE.le(a, b) -> ebool`
- `FHE.min(a, b) -> euintXX`
- `FHE.max(a, b) -> euintXX`

支持 encrypted-encrypted 和部分 encrypted-scalar 重载。`ebool` 不能作为 Solidity `bool` 使用。

## 布尔与位运算 API

布尔：

- `FHE.and(ebool, ebool/bool)`
- `FHE.or(ebool, ebool/bool)`
- `FHE.xor(ebool, ebool/bool)`
- `FHE.not(ebool)`

整数位运算：

- `FHE.and(euintXX, euintYY/scalar)`
- `FHE.or(euintXX, euintYY/scalar)`
- `FHE.xor(euintXX, euintYY/scalar)`
- `FHE.not(euintXX)`
- `FHE.shl(euintXX, euintXX/scalar)`
- `FHE.shr(euintXX, euintXX/scalar)`
- `FHE.rotl(euintXX, euintXX/scalar)`
- `FHE.rotr(euintXX, euintXX/scalar)`

## 条件选择

- `FHE.select(ebool control, ebool a, ebool b) -> ebool`
- `FHE.select(ebool control, euintXX a, euintXX b) -> euintXX`
- `FHE.select(ebool control, eaddress a, eaddress b) -> eaddress`

这是 encrypted 条件分支的核心工具。不要尝试把 `ebool` 解成普通 `bool` 后在链上 `if` 分支。

## 随机数

- `FHE.randEbool()`
- `FHE.randEuint8()` / `FHE.randEuint8(uint8 upperBound)`
- `FHE.randEuint16()` / `FHE.randEuint16(uint16 upperBound)`
- `FHE.randEuint32()` / `FHE.randEuint32(uint32 upperBound)`
- `FHE.randEuint64()` / `FHE.randEuint64(uint64 upperBound)`
- `FHE.randEuint128()` / `FHE.randEuint128(uint128 upperBound)`
- `FHE.randEuint256()` / `FHE.randEuint256(uint256 upperBound)`

使用随机数前确认当前网络和测试框架是否支持该路径，并为结果设置 ACL。

## ACL API

权限查询：

- `FHE.isAllowed(value, account) -> bool`
- `FHE.isSenderAllowed(value) -> bool`
- `FHE.isPubliclyDecryptable(value) -> bool`
- `FHE.isUserDecryptable(value, account, contractAddress) -> bool`
- `FHE.isAccountDenied(account) -> bool`

权限授予：

- `FHE.allow(value, account) -> value`
- `FHE.allowThis(value) -> value`
- `FHE.allowTransient(value, account) -> value`
- `FHE.makePubliclyDecryptable(value) -> value`

`allow`、`allowThis`、`allowTransient`、`makePubliclyDecryptable` 对 `ebool/euintXX/eaddress` 都有重载，并返回同一个 encrypted value，便于链式或赋值。

## User decrypt delegation

- `FHE.delegateUserDecryption(delegate, contractAddress, expirationDate)`
- `FHE.delegateUserDecryptionWithoutExpiration(delegate, contractAddress)`
- `FHE.delegateUserDecryptions(delegate, contractAddresses, expirationDate)`
- `FHE.delegateUserDecryptionsWithoutExpiration(delegate, contractAddresses)`
- `FHE.revokeUserDecryptionDelegation(delegate, contractAddress)`
- `FHE.revokeUserDecryptionDelegations(delegate, contractAddresses)`
- `FHE.isDelegatedForUserDecryption(delegate, delegator, contractAddress) -> bool`
- `FHE.getDelegatedUserDecryptionExpirationDate(delegate, delegator, contractAddress) -> uint64`

delegation 适合智能钱包、代理解密或后端服务代用户发起解密的场景。默认不要加入，除非产品需求明确。

## Public decrypt / KMS 验证

- `FHE.checkSignatures(handlesList, cleartexts, decryptionProof)`：链上验证 public decrypt 结果。
- `FHE.verifyDecryptionEIP712KMSSignatures(handlesList, decryptedResult, decryptionProof) -> bool`
- `FHE.isPublicDecryptionResultValid(handlesList, cleartexts, decryptionProof) -> bool`
- `FHE.eip712Domain()`
- `FHE.getThreshold()`
- `FHE.getKmsSigners()`

public decrypt 会公开数据。只有当业务明确允许所有人知道结果时才使用。

## 地址比较

- `FHE.eq(eaddress, eaddress/address) -> ebool`
- `FHE.ne(eaddress, eaddress/address) -> ebool`

`eaddress` 适合隐私地址场景，但要谨慎设计授权和最终解密方式。

## Error 和事件

常见错误：

- `SenderNotAllowedToUseHandle(bytes32 handle, address sender)`
- `InvalidKMSSignatures()`
- `EmptyDecryptionProof()`
- `KMSSignatureThresholdNotReached(uint256 numSignatures)`
- `KMSInvalidSigner(address invalidSigner)`

事件：

- `PublicDecryptionVerified(bytes32[] handlesList, bytes abiEncodedCleartexts)`

调试失败时先看 revert error，再查 ACL、proof 绑定关系和 chain id。
