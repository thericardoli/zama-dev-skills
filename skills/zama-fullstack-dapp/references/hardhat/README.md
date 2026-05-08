# Hardhat 编排路径

当 `packages/contract` 使用 Hardhat + `@fhevm/hardhat-plugin` 时，按本文件串联具体 skills。

## 推荐结构

```text
packages/
├── contract/
│   ├── contracts/
│   ├── test/
│   ├── deploy/
│   ├── tasks/
│   ├── scripts/
│   ├── deployments/
│   ├── hardhat.config.ts
│   └── package.json
├── frontend/
│   └── src/
└── service/       # 可选
```

## 应读取的 Skills 和 References

合约逻辑：

- `zama-fhevm-solidity-core/SKILL.md`
- 需要 API 时读 `zama-fhevm-solidity-core/references/api.md`
- 需要理解协议和架构时读 `zama-fhevm-solidity-core/references/overview.md`

Hardhat 项目和测试：

- `zama-hardhat-contract-dev/SKILL.md`
- 新建或修配置：`references/hardhat-project.md`
- 部署 local/Sepolia：`references/deploy.md`
- 具体测试 API：按该 skill 的索引读取 testing、encrypt、decrypt-acl、public-decrypt、sepolia 等 reference

SDK 和客户端：

- `zama-sdk/SKILL.md`
- 自定义合约调用：`references/custom-contracts.md`
- React/wagmi 前端：`references/react-wagmi-nextjs.md`
- Node、service、proxy：`references/node-and-local.md`
- 配置 RPC/relayer/storage：`references/configuration.md`
- 授权、session、浏览器安全：`references/session-security.md`
- 错误处理：`references/errors-events.md` 和 `references/troubleshooting.md`

安全复核：

- `zama-fhevm-security-review/SKILL.md`
- 对照 `references/checklist.md` 和 `references/vulnerability-patterns.md`

## Hardhat 串联流程

1. 先用 core skill 定义合约的 encrypted state、输入 proof、ACL、解密方式和算术边界。
2. 用 Hardhat skill 创建或修复 `packages/contract`，确认 plugin、config、TypeChain、deploy、tasks 和测试结构。
3. 明确 local/mock 和 SDK runtime 的边界：
   - Hardhat mock tests 适合快速合约测试。
   - 浏览器/Node SDK 需要匹配真实或兼容的 relayer runtime。
   - 不要把 mock decrypt 等同于生产 user decrypt。
4. 部署脚本或 deploy task 把地址写到 `packages/contract/deployments/`，再同步给 `packages/frontend/src/contracts/`。
5. 用 SDK skill 选择 runtime：
   - Sepolia/browser：`RelayerWeb`
   - Node/service：`RelayerNode`
   - local cleartext demo：`RelayerCleartext`，前提是本地链和 host contracts 兼容
6. 前端或 Node 流程必须遵循 custom-contracts reference：encrypt -> contract write -> read handle -> authorize -> decrypt。
7. 如果有 `packages/service`，它只负责需要后端保密或后台执行的事情，例如 relayer proxy、public decrypt finalize、链上监听和 smoke test。

## Artifact 约定

Hardhat 部署应产出按网络区分的 artifact：

- `packages/contract/deployments/<network>/...`，保留 Hardhat/Hardhat Deploy 原始输出。
- `packages/contract/deployments/addresses.json`，整理成前端友好的 chain id -> contracts map。
- `packages/frontend/src/contracts/addresses.json`，从 canonical artifact 生成。

ABI 的来源优先级：

1. TypeChain 和 Hardhat artifacts。
2. 生成到 `packages/frontend/src/contracts` 的 JSON ABI。
3. 轻量模板可以手写 ABI，但必须在验证清单中检查它和 artifact 一致。

## 部署注意事项

- Sepolia 使用 Zama 官方 FHEVM host contracts 和 relayer config，不要把 local/mock host stack 部署到 Sepolia。
- 不要把 private key 写进 `.env`。Hardhat vars 也只是本地明文，生产应使用更安全 signer。
- 如果 `.env` 存放非 secret RPC URL，部署 wrapper/task 需要显式加载；不要依赖 `pnpm run` 自动加载。
- Hardhat task 中涉及 encrypted input 或 decrypt 时，先按 Hardhat skill 初始化 plugin CLI API。

## 验证清单

- `packages/contract`：Hardhat compile、mock tests、TypeChain 生成。
- 合约测试：至少覆盖 encrypted input、运算、ACL、proof target 错误。
- `packages/frontend`：typecheck/build/test。
- local：明确这是 mock-only、SDK-compatible local，还是直接指向 Sepolia。
- Sepolia：deploy command 要么成功，要么在 signer/RPC 配置缺失时清晰失败。
- SDK smoke：可行时完成一笔 encrypt/write/read/decrypt。
- README：说明 packages 结构、local/mock/Sepolia 区别、前端配置、service 可选职责和用户必须提供的 secret/resource。
