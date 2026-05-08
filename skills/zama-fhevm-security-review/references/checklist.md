# FHEVM 安全 Checklist

## 0. 基础信息

- 依赖版本：`@fhevm/solidity`、Hardhat/Foundry plugin、`@zama-fhe/sdk`、React SDK、OpenZeppelin contracts。
- 目标网络：mock/local/Sepolia/mainnet。记录 chain id、ACL/KMS/InputVerifier/Gateway/Relayer 配置来源。
- 合约是否继承正确网络配置，例如 `ZamaEthereumConfig`；不要把 local/mock host 地址硬编码到 Sepolia。
- 部署 signer/RPC 是否 fail fast；live network 不允许默认 mnemonic、占位 RPC、空 accounts。

## 1. 隐私边界

- 哪些值必须始终保密：余额、bid、vote、position、location、secret、private order size。
- 哪些值业务上允许公开：final result、public tally、unwrap amount、settlement price。
- 哪些边界天然公开：ERC20 approve/transfer amount、shield amount、withdraw amount、事件 metadata、gas/time。
- README/UI 是否清楚说明公开边界，避免暗示 shield/unwrap 的金额也保密。
- 对“泄露后无法撤回”的信息是否有 finality delay 或两阶段授权。

## 2. Encrypted Input

- 用户输入是否使用 `externalEbool`、`externalEaddress`、`externalEuintXX` 和 `bytes inputProof`。
- 每个 untrusted encrypted input 是否调用 `FHE.fromExternal(input, inputProof)`。
- 是否存在 `euintXX.wrap(bytes32)`、直接 cast、或 `FHE.asEuintXX` 接收用户 calldata 的路径。
- SDK/测试生成 encrypted input 时，contract address 和 user/caller address 是否与最终 `msg.sender` 一致。
- 多个 encrypted inputs 若共用同一个 proof，handles index、proof 顺序和参数语义是否一致；若每个 input 单独 proof，是否逐个与对应参数匹配。
- 第三方 caller 场景是否可重放：timelock、router、relayer、multisig、batcher 是否能被攻击者触发复用同一 tuple。

## 3. ACL 和 Handle 生命周期

- 每个 storage handle 更新后，如果合约后续还要继续计算，是否调用 `FHE.allowThis(handle)`。
- 用户需要 user decrypt 的 handle 是否 `FHE.allow(handle, user)`；recipient/operator/spender 是否按业务授权。
- 是否存在过度授权 owner/admin/service，导致他们能读取用户机密。
- 跨合约 helper 只在当前交易需要权限时，是否优先 `FHE.allowTransient`。
- 使用持久 `FHE.allow` 给 helper/router/executor 时，是否能解释长期访问是否安全。
- 接收外部 handle 的 helper 是否调用 `FHE.isSenderAllowed(handle)` 或等价检查。
- 旧 handle 被替换后，旧权限是否仍可能泄露历史敏感值；业务是否接受历史可读性。
- 是否暴露任意 `execute(target,data)`，使持有权限的合约能调用 ACL 或把 handle 权限转出。

## 4. 算术、条件和业务不变量

- `euint` 算术是否有 wrap 风险：`add`、`sub`、`mul`、`shl`、decimal scaling、fee numerator。
- 是否用 encrypted guard + `FHE.select` 处理上限、余额不足、allowance 不足、overflow fallback。
- silent failure 是否被上层业务理解：confidential token transfer 可能返回 0/effective amount，auction/order/vault 不能只看 requested amount。
- `ebool` 是否错误用于 Solidity `if/require` 或暗示同步 revert。
- 是否用公开变量维护 backing/liability/supply 不变量，并和 confidential accounting 对齐。
- decimals 是否明确：USDC/cUSDC 通常 6 decimals；若支持任意 decimals，scaling 与 uint64 上限要测试。
- HCU 是否可能超限；循环、批处理、深层组合是否拆分交易或限制 batch size。

## 5. User Decrypt

- 合约是否只给应读取者授权；view 函数返回 handle 不等于可解密权限。
- 前端是否以当前 account、chain、contractAddress 请求 decrypt；账户或网络切换后是否清理旧结果。
- session/keypair 是否有 TTL；disconnect/account change 后是否 revoke 或刷新。
- 是否处理 zero/uninitialized handle；避免把 `0x00` 当成真实余额或继续 decrypt。
- 是否有未授权用户 decrypt 失败测试。
- 批量 decrypt 是否考虑 SDK bit-length 限制和错误状态。

## 6. Public Decrypt / Async Finalize

- `FHE.makePubliclyDecryptable` 是否只用于允许永久公开的数据。
- 请求是否记录 request id、requester、recipient、handles、expected type/order、deadline/status。
- `FHE.checkSignatures` 的 handles 数量、顺序、cleartext ABI types 是否与 off-chain `publicDecrypt` 输入一致。
- finalize/callback 是否先 consume/close request，再转账、mint/burn、外部调用或发放权限。
- 是否防止 replay：同一 proof 重复 finalize、跨 request 使用、已取消/过期 request 使用。
- 是否限制或验证 caller/gateway/relayer 假设；如果任何人可 finalize，是否依赖 proof 而不是 caller 信任。
- 失败路径是否能恢复：false predicate、zero debit、过期、cancel、KMS/relayer liveness failure。

## 7. Reorg、Finality 和 AA

- 关键秘密授权是否需要等待 finality，而不是付款交易同块或短窗口内立刻 `allow`。
- 买卖机密信息、sealed auction、秘密位置/私钥等场景是否采用 request -> finality delay -> grant decrypt。
- Account Abstraction/bundler 场景是否可能共享 transient allowance；是否要求 cleanup 或避免 AA 聚合调用。
- 是否依赖事件顺序或 mempool 观察作安全边界。

## 8. SDK、Relayer、Frontend、Service

- 前端是否正确加载 Zama SDK/React SDK，chain id、relayer URL、contract address、ABI 来自 canonical artifact。
- 浏览器是否暴露 private key、mnemonic、deployer key、relayer API key 或 backend signing credentials。
- Relayer/backend 是否负责 transaction submission、EIP-712 signing、nonce/retry/key management；不要让浏览器长期持有服务密钥。
- local cleartext/mock config 是否只在 local 使用；Sepolia/mainnet 禁止 cleartext runtime。
- registry/wrapper discovery 是否验证 result validity；不要硬编码未验证 cToken/wrapper 地址。
- SDK import 与本地安装版本是否一致；遇到 wagmi adapter mismatch，不要 patch `node_modules`，用已记录 fallback。
- UI 是否显示 loading/error/pending/finalized；不要在 transaction pending 时展示过期 plaintext。

## 9. 测试最低要求

- Wrong user、wrong contract、wrong proof、wrong handle order。
- 未授权 decrypt 失败；recipient/operator/admin 权限边界。
- Overflow/underflow、uint64 上限、decimals mismatch、zero amount/address。
- Insufficient balance silent failure 和 effective amount。
- Public decrypt proof 验证、replay、finalize twice、cancel/expired/false predicate。
- Reorg/finality 高价值授权流程的时间锁测试。
- HCU/batch size 上限测试。
- Sepolia/live 配置 fail-fast 测试：缺 RPC/signer 时清楚失败。

## 10. Severity 参考

- Critical：可无权限解密核心秘密、重放 public decrypt 提走资产、任意 executor 转出 ACL、资金 backing 被 admin/attacker 直接盗走。
- High：silent failure 破坏拍卖/清算/提现核心不变量、overflow 导致系统性少收费或多铸、错误 recipient 授权泄露敏感余额。
- Medium：生产路径不可用或可 DoS、session/chain 混用导致错误展示、registry/wrapper 可被错误配置、HCU 可被用户轻易打爆。
- Low：文档误导隐私边界、测试只覆盖 mock happy path、事件或 getter 命名混淆、gas/可维护性问题。
