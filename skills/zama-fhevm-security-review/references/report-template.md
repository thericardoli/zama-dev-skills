# Review 报告模板

## Findings

### High

格式：

```text
HIGH: 标题
位置：contracts/X.sol:123
问题：说明具体错误。
影响：说明攻击者或误用者能造成什么后果。
修复：给出最小修改方向。
测试：说明应新增的测试。
```

### Medium

同上。

### Low

同上。

## Open Questions

列出无法从代码确认但会影响安全判断的问题，例如：

- 某个 handle 是否设计上允许公开？
- relayer/gateway 地址是否固定可信？
- 是否要求 recipient 能解密余额？
- 是否需要支持链重组后的 callback 重试？

## Test Gaps

列出缺失测试：

- 未授权用户 decrypt
- 多用户 transfer
- 边界值和 wrapping
- public decrypt replay
- Sepolia 或真实 SDK 流程

## Summary

简短总结整体风险和最重要的下一步。不要把 summary 放在 findings 前面。
