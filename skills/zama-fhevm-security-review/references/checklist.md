# FHEVM 安全 Checklist

## 输入

- 外部 encrypted input 是否使用 `externalEuintXX`？
- 是否调用 `FHE.fromExternal(input, proof)`？
- proof 是否绑定正确 user 和 contract？
- 是否存在把 `bytes32` wrap 成 encrypted type 的用户输入路径？
- 是否错误使用 `FHE.asEuintXX` 接收不可信输入？

## ACL

- 状态 handle 更新后是否调用 `FHE.allowThis`？
- 需要读取的用户是否被 `FHE.allow(handle, user)` 授权？
- recipient、spender、operator、owner、callback contract 是否需要权限？
- 是否对不需要的人授权？
- transient authorization 是否只用于短生命周期调用？
- 旧 handle 权限是否会造成长期泄露？

## 解密

- user decrypt 是否只面向被授权用户？
- public decrypt 是否只用于可公开数据？
- public decrypt request 和 callback 是否绑定 request id？
- cleartexts、handles、proof 顺序是否一致？
- 是否检查 caller/gateway？
- 是否考虑 replay 和重复 callback？
- 是否考虑链重组和确认数？

## 算术和业务逻辑

- `FHE.add`、`FHE.sub` 是否可能 wrapping？
- 余额不足时是否 fail-closed？
- encrypted comparison 结果是否通过 `FHE.select` 正确使用？
- 有没有把 encrypted bool 当普通 bool？
- 上限、下限、限额、次数限制是否可测试？

## 前端和 relayer

- SDK chain id 是否匹配钱包和合约地址？
- local cleartext config 是否只用于本地？
- 解密结果是否只展示给当前授权钱包？
- session/keypair 缓存是否会跨账户误用？
- 是否处理 zero handle？

## 测试

- 是否有未授权 decrypt 失败测试？
- 是否有多用户授权测试？
- 是否有边界值测试？
- 是否有 public decrypt proof 顺序/重复回调测试？
- 是否至少有一个真实 SDK/relayer 集成路径测试？
