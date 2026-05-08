# FHEVM Security Review 报告模板

## Findings

按严重程度排序。不要先写长总结。

### Critical / High / Medium / Low

每个 finding 使用这个结构：

```text
标题：一句话说明具体问题
位置：contracts/X.sol:123 或 packages/frontend/src/Y.tsx:45
严重性：High

问题：
说明代码具体做错了什么。指出相关 handle、ACL、proof、SDK session、public decrypt request 或 business invariant。

影响：
说明攻击者或误用者能造成什么后果，例如无权限解密、重复提现、空转账赢拍卖、错误用户看到明文、Sepolia 部署使用默认 mnemonic。

场景：
列出最小攻击/失败路径。FHEVM 问题要说明 mock 下为什么可能不暴露、生产路径为什么会暴露。

修复：
给出最小可执行修改方向。必要时说明应使用 `FHE.fromExternal`、`FHE.isSenderAllowed`、`allowTransient`、`FHE.select`、request consume、finality delay、SDK session cleanup 等。

测试：
列出应该新增或修改的测试，包括 wrong user/contract proof、unauthorized decrypt、replay、wrong handle order、overflow、insufficient balance silent failure、live config fail-fast。
```

## Trust Assumptions

简短列出评审依赖的假设：

- 目标网络和 FHEVM 版本。
- KMS/Gateway/Relayer 信任和 liveness 假设。
- 是否允许任何人 finalize public decrypt。
- 哪些数据产品上允许公开。
- 是否支持 Account Abstraction、routers、batchers、multisigs。
- 是否使用 OpenZeppelin confidential contracts、ERC7984、wrapper registry。

## Privacy Boundary

用表格或短列表说明：

- Private：必须一直保密的值。
- Public by design：业务最终公开的值。
- Public boundary：ERC20 shield/unwrap、事件、交易 metadata。
- Authorized readers：每个 handle 谁能 user decrypt。
- Permanent public decrypt：哪些 handle 被 `makePubliclyDecryptable`，为什么。

## Test Gaps

列出缺失测试，不要只说“需要更多测试”：

- input proof：wrong user、wrong contract、wrong order、replay。
- ACL：未授权 decrypt 失败、recipient/operator 权限、helper 权限。
- arithmetic：overflow、underflow、uint64 max、decimals scaling。
- silent failure：insufficient balance、effective transferred/debited amount。
- public decrypt：proof order、finalize twice、cancel/expired/false predicate。
- SDK：account/chain switch、zero handle、session expiry、relayer error。
- deployment：live network missing signer/RPC fail-fast。

## Positive Notes

只列真正有价值的安全设计，例如：

- request 在外部调用前 consume。
- helper 使用 `isSenderAllowed`。
- public decrypt 只用于明确公开结果。
- live deployment 不使用默认 mnemonic。
- 前端不暴露 secret，artifact 自动同步。

## Summary

最后用 3-5 句总结：

- 总体风险等级。
- 最重要的 1-2 个修复。
- 哪些问题属于实现质量，哪些可能源于 skill/docs 误导。
- 下一步建议：补测试、改设计、上 Sepolia smoke test、人工审计。
