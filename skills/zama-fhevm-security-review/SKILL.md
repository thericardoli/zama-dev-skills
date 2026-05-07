---
name: zama-fhevm-security-review
description: 审计或安全评审 Zama FHEVM confidential smart contracts 和前端集成时使用。适用于 ACL 漏洞、错误解密、public decrypt 泄露、input proof、replay、reorg、overflow/underflow、trivial encryption、mock 与生产差异、FHEVM 特有安全风险。
---

# Zama FHEVM Security Review

## 适用场景

当用户要求审计、review、找安全问题、评估漏洞、设计安全 checklist 或修复 FHEVM 合约风险时使用本 skill。

本 skill 关注 FHEVM 特有风险，同时不要忽略普通 Solidity 风险。

## Review 流程

1. **确认版本和运行环境**：Hardhat mock、forge-fhevm、本地 cleartext、Sepolia、Mainnet 的安全假设不同。
2. **画出隐私边界**：哪些值应该一直保密，哪些值最终可公开，谁能 user decrypt。
3. **追踪每个 handle 生命周期**：创建、验证、存储、计算、ACL、解密、公开、废弃。
4. **检查输入 proof**：所有用户输入是否都通过 `FHE.fromExternal` 验证。
5. **检查 ACL**：合约自身、sender、recipient、operator、callback contract 是否授权正确，是否过度授权。
6. **检查解密流程**：user decrypt/public decrypt 是否绑定 request、handle、caller、chain 和生命周期。
7. **检查算术和业务约束**：余额、限额、计数器、票数是否存在 wrapping 或 fail-open。
8. **检查测试是否覆盖真实风险**：不能只靠 mock happy path。

## 输出要求

安全 review 输出优先列问题，按严重程度排序。每个问题应包含：

- 文件和行号
- 风险描述
- 可利用或误用场景
- 修复建议
- 建议测试

如果没有发现高危问题，也要说明剩余风险和测试缺口。

## 需要加载的参考

- FHEVM 安全 checklist：读 `references/checklist.md`
- 常见漏洞模式：读 `references/vulnerability-patterns.md`
- Review 报告模板：读 `references/report-template.md`

## 常见高危信号

- 未验证外部 encrypted input
- 忘记或错误使用 ACL
- 把 private state 标记为 publicly decryptable
- public decrypt callback 没有 replay protection
- user decrypt 授权给错误地址
- 使用 trivial encryption 接收不可信用户输入
- mock 测试通过，但 Sepolia/真实 relayer 流程不可用
- encrypted 条件检查失败时仍更新状态
