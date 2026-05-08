# Foundry 编排路径

当 `packages/contract` 使用 Foundry/Forge + `forge-fhevm` 时，按本文件串联具体 skills。

## 推荐结构

```text
packages/
├── contract/
│   ├── src/
│   ├── test/
│   ├── script/
│   ├── scripts/
│   ├── deployments/
│   ├── foundry.toml
│   └── package.json
├── frontend/
│   └── src/
└── service/
```

## 应读取的 Skills 和 References

合约逻辑：

- `zama-fhevm-solidity-core/SKILL.md`
- 需要 API 时读 `zama-fhevm-solidity-core/references/api.md`
- 需要理解协议和架构时读 `zama-fhevm-solidity-core/references/overview.md`

Foundry 项目和测试：

- `zama-foundry-forge-fhevm/SKILL.md`
- 新建或修配置：`references/foundry-project.md`
- 部署 local/Sepolia：`references/deploy.md`
- 具体测试 API：按该 skill 的索引读取 testing、encrypt、decrypt、acl、fuzz 等 reference

SDK 和客户端：

- `zama-sdk/SKILL.md`
- 自定义合约调用：`references/custom-contracts.md`
- React/wagmi 前端：`references/react-wagmi-nextjs.md`
- Node、本地 cleartext、service：`references/node-and-local.md`
- 配置 RPC/relayer/storage：`references/configuration.md`
- 授权、session、浏览器安全：`references/session-security.md`
- 错误处理：`references/errors-events.md` 和 `references/troubleshooting.md`

安全复核：

- `zama-fhevm-security-review/SKILL.md`
- 对照 `references/checklist.md` 和 `references/vulnerability-patterns.md`

## Foundry 串联流程

1. 先用 core skill 定义合约的 encrypted state、输入 proof、ACL、解密方式和算术边界。
2. 用 Foundry skill 创建或修复 `packages/contract`，确认 `foundry.toml`、Soldeer 依赖、remappings、Forge 测试和部署脚本。
3. 用 Foundry deploy reference 处理两层 local：
   - Anvil 上的 `forge-fhevm` local cleartext host stack。
   - dApp 合约部署。
4. 部署脚本把地址写到 `packages/contract/deployments/`，再同步给 `packages/frontend/src/contracts/`。
5. 用 SDK skill 选择 runtime：
   - local cleartext：`RelayerCleartext`
   - Sepolia/browser：`RelayerWeb`
   - Node/service：`RelayerNode`
6. 前端或 Node 流程必须遵循 custom-contracts reference：encrypt -> contract write -> read handle -> authorize -> decrypt。
7. 如果有 `packages/service`，它只负责需要后端保密或后台执行的事情，例如 relayer proxy、public decrypt finalize、链上监听和 smoke test。

## Artifact 约定

Foundry 部署脚本应写出按网络区分的 artifact：

- `packages/contract/deployments/local.json`
- `packages/contract/deployments/sepolia.json`
- `packages/contract/deployments/addresses.json`
- `packages/frontend/src/contracts/addresses.json`

`addresses.json` 应按 chain id 分组。不要用单个 `deployment.json` 覆盖所有网络。

ABI 的来源优先级：

1. Foundry 编译 artifact 自动生成或复制。
2. 轻量模板可以手写 ABI，但必须在验证清单中检查它和编译 artifact 一致。

## 部署注意事项

- Sepolia 不需要运行 `forge-fhevm/deploy-local.sh`。
- 测试网或生产部署使用 Foundry keystore、硬件钱包或受控 signer，不要把 private key 放进 `.env`。
- 根脚本可以调用 `packages/contract` 里的部署 wrapper；wrapper 负责加载 `.env`、检查 `SEPOLIA_RPC_URL`、`DEPLOYER_ACCOUNT`、keystore、可选 verify key。
- 如果部署脚本写文件，Foundry `fs_permissions` 必须覆盖 `packages/contract/deployments` 和 `packages/frontend/src/contracts`。

## 验证清单

- `packages/contract`：Soldeer install、Forge build、Forge tests。
- 合约测试：至少覆盖 encrypted input、运算、ACL、proof target 错误。
- `packages/frontend`：typecheck/build/test。
- local：Anvil + FHEVM host stack + dApp deploy 的步骤明确。
- Sepolia：deploy command 要么成功，要么在 env/keystore 缺失时清晰失败。
- SDK smoke：可行时完成一笔 encrypt/write/read/decrypt。
- README：说明 packages 结构、local/Sepolia、前端配置、service 可选职责和用户必须提供的 secret/resource。
