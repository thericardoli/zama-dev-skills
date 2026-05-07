# Zama Skill Map

## `zama-fhevm-solidity-core`

职责：

- 解释 Zama Protocol 和 fhevm-solidity 的合约侧模型
- 查询 encrypted 类型和 `FHE` API
- 设计 Solidity 合约内 encrypted input、operations、ACL、decrypt、ERC7984 等模式

边界：

- 不写 Hardhat/Foundry 测试流程
- 不写 React hooks 或 SDK runtime 初始化
- 不负责部署命令

优先使用场景：

- “写一个 FHEVM 合约”
- “这个 `FHE.allowThis` 是干什么的”
- “如何实现 confidential transfer”
- “ERC7984 token 合约怎么集成”

## `zama-hardhat-contract-dev`

职责：

- Hardhat 项目结构、依赖、配置
- `@fhevm/hardhat-plugin`
- TypeScript 测试中的 encrypted input 和 decrypt helper
- Hardhat deploy、localhost、Sepolia、task

边界：

- Solidity 业务模式仍应回到 `zama-fhevm-solidity-core`
- 不负责 React provider/hook 设计
- 不负责 Foundry 测试

优先使用场景：

- “用 Hardhat 测试这个 Zama 合约”
- “`fhevm.createEncryptedInput` 怎么用”
- “部署到 Sepolia”

## `zama-foundry-forge-fhevm`

职责：

- Foundry 项目配置
- `forge-fhevm`、`FhevmTest`
- Forge tests、fuzz tests、local cleartext stack
- Foundry deploy script

边界：

- Solidity 合约模式仍应回到 `zama-fhevm-solidity-core`
- 不负责 Hardhat plugin
- 不负责 React/Zama SDK UI

优先使用场景：

- “用 Foundry 写 FHEVM 测试”
- “`encryptUint64` / `decrypt` / `userDecrypt` 怎么用”
- “forge-fhevm 编译失败”

## `zama-sdk`

职责：

- 新版 `@zama-fhe/sdk` 和 `@zama-fhe/react-sdk`
- Browser/Node/local cleartext relayer runtime
- React/Next.js/wagmi/viem/ethers 前端和脚本接入
- encrypted input 生成、user decrypt、public decrypt、delegated decrypt
- ERC7984 confidential token、wrapper registry、token hooks
- Sepolia/Mainnet/local relayer config
- 替代旧 relayer/react-wagmi skill 的统一入口

边界：

- 合约 ACL 和 decrypt 设计回到 `zama-fhevm-solidity-core`
- Hardhat/Foundry 测试 helper 回到对应框架 skill

优先使用场景：

- “写一个 Node 脚本调用 Zama 合约”
- “Zama SDK 怎么初始化”
- “用 viem 发送 encrypted input”
- “做一个 React 页面连接 Zama 合约”
- “`useEncrypt` / `useUserDecrypt` 怎么用”
- “本地 31337 和 Sepolia runtime 怎么切换”

## `zama-fhevm-security-review`

职责：

- FHEVM 合约和前端集成安全审计
- ACL、proof、public decrypt、replay、reorg
- overflow/underflow、encrypted condition fail-open
- mock 与生产差异

边界：

- 不作为普通开发入口
- 发现具体实现问题时，可按需读取 core 或框架 skill

优先使用场景：

- “review 这个 Zama 合约”
- “有哪些安全问题”
- “检查 ACL 是否正确”
- “public decrypt callback 是否安全”

## 选择规则

- 只涉及合约：core
- 合约 + Hardhat 测试：core + hardhat
- 合约 + Foundry 测试：core + foundry
- 合约 + React：core + `zama-sdk`
- 脚本/CLI：core + `zama-sdk`
- 审计：security，必要时加 core 或框架 skill
- 用户没说框架：先 core，除非 repo 结构能判断 Hardhat/Foundry/React
