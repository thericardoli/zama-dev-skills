# Foundry 项目配置

核心原则：

- 默认使用 Soldeer 管理依赖。
- 普通 Soldeer 包可以使用 `latest`。
- `forge-fhevm` 和 `@openzeppelin-confidential-contracts` 使用 git URL，并固定到最新 `rev`。
- Solidity 编译器版本必须不低于 `0.8.27`。
- EVM 版本必须不低于 `cancun`。
- 不能使用 Soldeer 时，再使用 git submodule fallback。

## 版本与 rev

创建或更新项目时，先刷新两个 git dependency 的最新 `rev`：

```bash
git ls-remote https://github.com/zama-ai/forge-fhevm HEAD
git ls-remote https://github.com/OpenZeppelin/openzeppelin-confidential-contracts HEAD
```

## 推荐 foundry.toml

```toml
[profile.default]
src = "src"
out = "out"
libs = ["dependencies"]
test = "test"
script = "script"
solc = "0.8.27"
evm_version = "cancun"
optimizer = true
optimizer_runs = 800
cbor_metadata = false
bytecode_hash = "none"

[fuzz]
runs = 256

[fmt]
line_length = 120

[dependencies]
forge-std = "latest"
"@fhevm-solidity" = "latest"
"@encrypted-types" = "latest"
"@openzeppelin-contracts" = "latest"
"@openzeppelin-contracts-upgradeable" = "latest"
forge-fhevm = { version = "60864a0", git = "https://github.com/zama-ai/forge-fhevm.git", rev = "60864a00bc7f5361c9026d80ca34e40687a6d2d2" }
"@openzeppelin-confidential-contracts" = { version = "03ffadd", git = "https://github.com/OpenZeppelin/openzeppelin-confidential-contracts.git", rev = "03ffaddf3520532fc396ecc612f10799335dd569" }

[soldeer]
remappings_version = false
recursive_deps = true
```

说明：

- `solc = "0.8.27"` 是最低推荐值。已有项目可以使用更新编译器，但不要低于 `0.8.27`。
- `evm_version = "cancun"` 是最低推荐 EVM 版本。已有项目可以使用更新 EVM 版本，但不要低于 `cancun`。
- `optimizer_runs = 800` 是推荐起点；如果项目已有明确 gas/bytecode 策略，遵循项目配置。
- 如果项目不使用 upgradeable contracts，可以删除 `@openzeppelin-contracts-upgradeable`。
- 如果项目不使用 ERC7984 或 OpenZeppelin confidential contracts，可以删除 `@openzeppelin-confidential-contracts`。

## 安装命令

```bash
forge soldeer install
forge build
forge test -vv
```

不要优先使用 Foundry 的 git 安装命令直接安装 `zama-ai/forge-fhevm`。它会走 `lib/` 风格依赖布局，容易和 Soldeer 的 `dependencies/`、`soldeer.lock`、版本化 remappings 混在一起。

## 依赖包作用

- `forge-std`：Foundry 标准库，提供 `Test`、`Script`、cheatcodes helper。
- `@fhevm-solidity`：Zama FHEVM Solidity 合约库，提供 `FHE`、`ZamaConfig` 等核心合约 API。
- `@encrypted-types`：encrypted type 定义，例如 `euint32`、`externalEuint32`。
- `forge-fhevm`：Foundry-native FHEVM 测试库，提供 `FhevmTest`、加密/解密 helper、本地 cleartext host contracts。
- `@openzeppelin-contracts`：普通 OpenZeppelin contracts，例如 `Ownable`、`ReentrancyGuard`、ERC721/ERC20 接口。
- `@openzeppelin-contracts-upgradeable`：OpenZeppelin upgradeable contracts；只在项目需要 upgradeable 模式时保留。
- `@openzeppelin-confidential-contracts`：OpenZeppelin confidential contracts，例如 ERC7984 相关接口和实现。

## remappings

Soldeer 安装后会在 `dependencies/` 下创建带版本标签的目录。由于普通包使用 `latest`，实际目录名取决于 Soldeer resolve 出来的版本；不要在 skill 中硬编码普通包的版本后缀。

推荐写法是安装后确认目录：

```bash
find dependencies -maxdepth 1 -type d | sort
forge remappings
```

然后按实际目录写 `remappings.txt`。模板如下：

```text
@fhevm/host-contracts/=dependencies/forge-fhevm-60864a0/src/fhevm-host/
@fhevm/solidity/=dependencies/@fhevm-solidity-<resolved-version>/
@openzeppelin-contracts-upgradeable/=dependencies/@openzeppelin-contracts-upgradeable-<resolved-version>/
@openzeppelin-contracts/=dependencies/@openzeppelin-contracts-<resolved-version>/
@openzeppelin/confidential-contracts/=dependencies/@openzeppelin-confidential-contracts-03ffadd/contracts/
encrypted-types/=dependencies/@encrypted-types-<resolved-version>/
forge-fhevm/=dependencies/forge-fhevm-60864a0/src/
forge-std/=dependencies/forge-std-<resolved-version>/src
```

如果刷新了 git dependency 的 `rev`，同步更新：

- `foundry.toml` 中的 `version` 和 `rev`
- `soldeer.lock`
- `remappings.txt` 中 `forge-fhevm-<version>` 和 `@openzeppelin-confidential-contracts-<version>` 路径

## 目录结构

推荐：

```text
foundry/
├── foundry.toml
├── remappings.txt
├── soldeer.lock
├── src/
├── test/
└── script/
```

不要把 `node_modules` 当作 Foundry dependency 源。Foundry 合约依赖应来自 `dependencies/` 或 fallback 的 `lib/`。

## Git submodule fallback

只有在项目不能使用 Soldeer 时，才使用 submodule。保持依赖来源一致，不要同一项目里同时维护 `dependencies/forge-fhevm-*` 和 `lib/forge-fhevm`。

```bash
git submodule add https://github.com/zama-ai/forge-fhevm.git lib/forge-fhevm
git submodule add https://github.com/foundry-rs/forge-std.git lib/forge-std
git submodule add https://github.com/OpenZeppelin/openzeppelin-contracts.git lib/openzeppelin-contracts
git submodule add https://github.com/OpenZeppelin/openzeppelin-contracts-upgradeable.git lib/openzeppelin-contracts-upgradeable
git submodule add https://github.com/OpenZeppelin/openzeppelin-confidential-contracts.git lib/openzeppelin-confidential-contracts
git submodule update --init --recursive
```

submodule 布局下，`foundry.toml` 通常改为：

```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
test = "test"
script = "script"
solc = "0.8.27"
evm_version = "cancun"
optimizer = true
optimizer_runs = 800
cbor_metadata = false
bytecode_hash = "none"
```

submodule remappings 必须指向真实目录。例如：

```text
forge-fhevm/=lib/forge-fhevm/src/
@fhevm/host-contracts/=lib/forge-fhevm/src/fhevm-host/
forge-std/=lib/forge-std/src/
@openzeppelin-contracts/=lib/openzeppelin-contracts/contracts/
@openzeppelin-contracts-upgradeable/=lib/openzeppelin-contracts-upgradeable/contracts/
@openzeppelin/confidential-contracts/=lib/openzeppelin-confidential-contracts/contracts/
```

`@fhevm/solidity` 和 `encrypted-types` 如果没有通过 Soldeer 安装，需要确认是否由 `forge-fhevm` vendored，或单独以 submodule/本地依赖提供。不要照抄 Soldeer 的 `dependencies/...` remapping 到 `lib/` 项目。

## 编译排查

编译错误优先检查：

- `solc` 是否不低于 `0.8.27`
- `evm_version` 是否不低于 `cancun`
- `libs` 是否和依赖目录一致：Soldeer 用 `dependencies`，submodule 用 `lib`
- `remappings.txt` 里的版本后缀是否真实存在
- 是否同时混入了 `dependencies/forge-fhevm-*` 和 `lib/forge-fhevm`
- 是否把 Hardhat `node_modules` import 当作 Foundry remapping
- `@fhevm/solidity` 和 `encrypted-types` 是否来自兼容版本
