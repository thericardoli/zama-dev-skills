---
name: zama-fhevm-security-review
description: 审计、review、威胁建模或修复 Zama FHEVM confidential contracts 与 SDK/frontend 集成时使用。覆盖 encrypted input proof、ACL/handle 权限、user/public decrypt、async callback replay、silent failure、unchecked encrypted arithmetic、transient allowance、AA/reorg/finality、HCU、ERC7984/wrapper、Relayer SDK、React/wagmi、Node service、部署和测试缺口。
---

# Zama FHEVM Security Review

## 适用场景

当用户要求审计、review、找漏洞、解释风险、补安全测试、修复 confidential contract 或检查前端/SDK 集成时使用本 skill。

本 skill 是 FHEVM 专项安全流程，不替代普通 Solidity 审计。发现 reentrancy、access control、admin key、upgrade、ERC20 accounting、oracle、DoS、deployment secret 等传统问题时，也要一并报告。

## 先读哪个 reference

- 审计完整项目或做 checklist：读 `references/checklist.md`
- 需要定位 FHEVM 特有漏洞：读 `references/vulnerability-patterns.md`
- 用户要求正式 review 输出：读 `references/report-template.md`

需要代码/API 细节时组合其它 skills：

- 合约 API 和 FHE 语义：`zama-fhevm-solidity-core`
- Hardhat 测试、mock、Sepolia：`zama-hardhat-contract-dev`
- Foundry/forge-fhevm：`zama-foundry-forge-fhevm`
- React/Node/Relayer SDK：`zama-sdk`

## 审计心智模型

FHEVM 安全的核心不是“值已经加密所以安全”，而是：

1. **Handle 是能力引用**：链上保存的是 ciphertext handle；谁能计算、传递、解密由 ACL 决定。
2. **合约不能直接分支 encrypted bool**：比较结果是 `ebool`，业务逻辑必须用 `FHE.select` 或异步 decrypt 设计。
3. **encrypted arithmetic 默认 unchecked**：溢出/下溢不会像 Solidity checked math 一样 revert，通常会 wrap。
4. **public decrypt 是永久公开语义**：`makePubliclyDecryptable` 后任何人都能请求 cleartext。
5. **user decrypt 是 ACL + session/signature 流程**：前端能显示不代表合约授权正确；合约授权和 SDK 签名上下文都要检查。
6. **mock/local 与 Sepolia/mainnet 假设不同**：mock decrypt helper 不能证明生产 ACL、relayer、KMS、Gateway、reorg/finality 路径安全。

## Review 流程

1. **确定版本和运行环境**
   - 记录 `@fhevm/solidity`、Hardhat/Foundry plugin、`@zama-fhe/sdk`/React SDK、OpenZeppelin contracts 版本。
   - 区分 Hardhat mock、Foundry cleartext/local、Sepolia、mainnet。不要把 mock-only helper 的通过当成真实安全证明。

2. **画隐私边界**
   - 列出应保密的字段、允许公开的字段、边界公开字段（shield/unwrap amount、事件、public decrypt 结果）。
   - 标出谁应该 user decrypt：owner、recipient、operator、admin、service、任何人。
   - 标出泄露不可逆的信息，例如 sealed bid、投票、私钥、坐标、清算价格、订单规模。

3. **追踪每个 handle 生命周期**
   - 来源：`FHE.fromExternal`、trivial encryption、random、其它合约返回、storage 旧值。
   - 使用：运算、比较、传给 helper、存储、事件、返回 view。
   - 权限：`allowThis`、`allow`、`allowTransient`、`makePubliclyDecryptable`、`isSenderAllowed`/`isAllowed`。
   - 终点：user decrypt、public decrypt、callback/finalize、废弃或覆盖。

4. **检查输入和上下文绑定**
   - 不可信用户输入必须是 `externalE* + inputProof` 并经 `FHE.fromExternal` 验证。
   - SDK/测试生成 encrypted input 时，contract address、user/caller address、chain、参数顺序必须和 Solidity 消费一致。
   - 第三方 caller（timelock、multisig、relayer、router）代用户提交 encrypted tuple 时，必须有额外绑定或中间合约自己验证，不能让任意触发者复用 calldata。

5. **检查 ACL 最小授权**
   - 每个持久 storage handle 更新后，合约后续还要用就必须 `allowThis`。
   - 只给真正需要 decrypt 或继续计算的一方授权；recipient、spender、operator、callback/helper contract 分别确认。
   - helper contract 消费传入 handle 前要验证 caller 对 handle 有权，尤其是 fee、router、auction、batcher、executor。
   - 跨合约临时调用优先 `allowTransient`；持久授权要能解释为什么不会成为长期泄露面。

6. **检查算术、silent failure 和业务不变量**
   - 对每个 `add/sub/mul/div/rem/shl` 评估 wrap 风险。金额、fee、decimals scaling、liability、votes、bid 都要有边界策略。
   - 余额不足、allowance 不足、bid 未实际转入等路径是否 fail-closed。若底层 confidential token 返回 effective transferred amount，业务必须用 effective amount，而不是用户请求 amount。
   - 不能把 `ebool` 当普通 `bool`。需要公开执行时，设计 async decrypt、proof 验证和 one-time finalize。

7. **检查 public decrypt / async finalize**
   - `makePubliclyDecryptable` 只用于业务允许公开的数据；一旦公开，不再假设隐私。
   - `checkSignatures` 的 handles、cleartexts、类型和顺序必须完全一致。
   - 每个 request 必须有 request id、owner/recipient、handle(s)、deadline/status；finalize 前先 consume/close，再外部调用或转账。
   - callback/finalize 必须防重放、重复执行、跨 request 混用 proof、过期请求、错误 caller/gateway 假设。

8. **检查 reorg、AA 和 transient storage**
   - 高价值信息解密授权不要和付款/状态更新在同一最终性窗口内完成；需要两步授权和 finality delay。
   - Account Abstraction bundling 下，多个 user operation 可能共享一次交易的 transient context；不要假设 transient allowance 在 AA 组合场景中天然隔离。
   - 有 FHEVM-sensitive AA flow 时，检查是否有 cleanup 策略或 wallet/bundler 层约束。

9. **检查 SDK、前端和服务端**
   - 浏览器不能暴露 private key、relayer API key、server signer、deployer key。
   - Relayer/API key/transaction signing 后端要做 key management、nonce/retry、typed-data signing 边界；前端只拿公开配置。
   - user decrypt session TTL、keypair storage、account/chain change、disconnect 后 revoke/refresh、zero handle、stale decrypt result 都要处理。
   - local cleartext/mock runtime 不得用于 Sepolia/mainnet；chain id、relayer URL、Gateway/ACL/KMS/InputVerifier 配置必须匹配目标网络。

10. **检查测试质量**
    - 必须有 wrong contract/user input proof、unauthorized user decrypt、over-authorized decrypt、ACL recipient/operator、多用户场景。
    - 必须有 overflow/underflow、insufficient balance silent failure、public decrypt proof order、replay/finalize twice、expired/cancelled request。
    - Sepolia/mainnet 路径至少有少量真实 SDK/relayer smoke test 或清楚说明外部资源。

## 输出要求

安全 review 输出 findings 优先，按严重程度排序。每个 finding 包含：

- 文件和行号
- 风险描述
- 可利用或误用场景
- 修复建议
- 建议测试

如果没有高危，也要说明剩余风险、信任假设和测试缺口。不要只给“看起来不错”的总结。

## 需要特别敏感的红旗

- 用户输入直接 wrap/cast 成 encrypted type，或使用 `FHE.asE*` 接收不可信输入。
- 存储新 handle 后忘记 `allowThis`，或只在 mock 测试里能跑。
- 对 helper/router/executor 授予长期 ACL，但 helper 不检查 `isSenderAllowed`。
- `makePubliclyDecryptable` 用在余额、投票、bid、订单、位置、私钥等应保密数据上。
- public decrypt finalize 不 consume request，或先转账/外部调用再关 request。
- 业务状态基于 requested encrypted amount 更新，没有确认 effective transferred/debited amount。
- encrypted arithmetic 参与 fee、liability、bid、vote power、decimals scaling 但没有 cap/select 策略。
- `execute(address,bytes)`、batcher、relayer、AA wallet 能从特权上下文任意调用 ACL 或受保护合约。
- 前端把旧账户/旧 chain 的 decrypt result 继续展示，或浏览器包含 API key/private key。

## 调研依据

- Zama Protocol docs：Encrypted inputs、ACL、public/user decrypt、supported types、HCU、reorg handling、Relayer SDK。
- OpenZeppelin：A Developer's Guide to FHEVM Security。
- OpenZeppelin audits：Zama Confidential Fungible Token、Confidential Vesting/Voting、Confidential Contracts batcher/diff。
