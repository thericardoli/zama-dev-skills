# Zama Workflow Map

## 新建或修改 Solidity 合约

读取顺序：

1. `zama-fhevm-solidity-core`
2. 只按需要读取 core references：
   - 类型和 API：`references/api.md`
   - 输入：`references/patterns/encryption.md`
   - 运算：`references/patterns/operations.md`
   - 条件分支：`references/patterns/branching.md`
   - ACL：`references/patterns/acl.md`
   - 解密：`references/patterns/decryption.md`

不要加载 Hardhat/Foundry，除非用户要求测试或仓库结构已经明确。

## Hardhat 合约开发

读取顺序：

1. `zama-fhevm-solidity-core`
2. `zama-hardhat-contract-dev`

常见任务：

- 写合约：先 core
- 写 TypeScript 测试：再 hardhat testing
- 部署：hardhat deploy references
- task：hardhat deploy-and-tasks references

## Foundry 合约开发

读取顺序：

1. `zama-fhevm-solidity-core`
2. `zama-foundry-forge-fhevm`

常见任务：

- 写合约：先 core
- 写 Forge test：foundry testing
- fuzz：foundry testing
- 本地 cleartext host contracts：foundry deploy

## React dApp

读取顺序：

1. `zama-fhevm-solidity-core`，理解合约 ABI、handle、ACL、decrypt 设计
2. `zama-sdk`
3. 在 `zama-sdk` 内按需选择 React hooks、provider、custom contract 或 token references

常见任务：

- 读 encrypted handle：React hook
- 写 encrypted input：React hook 或 `@zama-fhe/sdk`
- user decrypt：React hook
- 本地/Sepolia 切换：Zama provider/runtime config

## 脚本或 CLI

读取顺序：

1. `zama-fhevm-solidity-core`
2. `zama-sdk`

常见任务：

- Node 脚本加密输入
- viem/ethers 发送交易
- public decrypt 或 user decrypt
- 自定义 relayer/network config

## ERC7984 token

读取顺序：

1. `zama-fhevm-solidity-core`
2. core `references/patterns/erc7984.md`
3. 根据框架选择 Hardhat 或 Foundry
4. 如有前端，再读 `zama-sdk`

组合场景：

- token 合约：core ERC7984
- token 测试：hardhat/foundry
- token UI：`zama-sdk`
- wrapper/vesting/auction：core ERC7984 + ACL + branching/decryption

## Sealed-bid auction 或复杂应用

读取顺序：

1. core encryption
2. core operations
3. core branching
4. core ACL
5. core decryption
6. 如使用 ERC7984 收款，读 core ERC7984
7. 根据测试/前端需求加载框架 skill

典型结构：

- 用户提交 encrypted bid
- 合约用 `FHE.select` 更新 highest bid 和 encrypted winner
- 结束后 public decrypt winner
- finalize 验证 KMS proof 后写入公开 winner
- 普通 Solidity 逻辑处理 claim/withdraw

## 安全审计

读取顺序：

1. `zama-fhevm-security-review`
2. 如需确认合约 API 或模式，再读 `zama-fhevm-solidity-core`
3. 如风险来自测试或部署，再读 Hardhat/Foundry
4. 如风险来自 UI 或 SDK runtime，再读 `zama-sdk`

审计重点：

- 是否验证 encrypted input
- ACL 是否正确传播
- public decrypt 是否必要且防 replay
- encrypted condition 是否 fail-open
- 是否有 reorg 风险
- 测试是否只覆盖 mock happy path

## Debugging

读取顺序由报错位置决定：

- Solidity compile/API 错误：core api
- input proof/sender mismatch：core encryption + framework testing
- user decrypt failure：core ACL/decryption + framework/frontend skill
- public decrypt proof failure：core decryption + `zama-sdk`
- deploy/network 错误：Hardhat/Foundry deploy
- UI runtime 错误：`zama-sdk`
