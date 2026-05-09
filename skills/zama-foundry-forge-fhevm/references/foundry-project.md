# Foundry Project Configuration

Core principles:

- Use Soldeer for dependency management by default.
- Do not write FHE-related packages as `latest` in `foundry.toml`; `forge soldeer install` resolves `latest` as `@pkg~latest`, which can fail for some Zama packages.
- Start from the verified versions below; when upgrading, query the Soldeer registry or the git `rev`, then update `foundry.toml`, `soldeer.lock`, and `remappings.txt` together.
- Install `forge-fhevm` from its git URL and pin it to a verified `rev`.
- The Solidity compiler version must be at least `0.8.27`.
- The EVM version must be at least `cancun`.
- Use the git submodule fallback only when Soldeer cannot be used.

## Verified Versions

Prefer this version set to get the project running first:

| Dependency | Version |
| --- | --- |
| `forge-std` | `1.16.0` |
| `@fhevm-solidity` | `0.11.1` |
| `@encrypted-types` | `0.0.4` |
| `forge-fhevm` | git `60864a00bc7f5361c9026d80ca34e40687a6d2d2`, version label `60864a0` |

If the task explicitly requires ERC7984 or OpenZeppelin confidential contracts, add the corresponding dependencies as well. Standard custom encrypted-state contracts such as counters, vaults, and auctions usually do not need OpenZeppelin confidential contracts.

When updating `forge-fhevm`, refresh the git dependency `rev` first:

```bash
git ls-remote https://github.com/zama-ai/forge-fhevm HEAD
```

## Recommended foundry.toml

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
forge-std = "1.16.0"
"@fhevm-solidity" = "0.11.1"
"@encrypted-types" = "0.0.4"
forge-fhevm = { version = "60864a0", git = "https://github.com/zama-ai/forge-fhevm.git", rev = "60864a00bc7f5361c9026d80ca34e40687a6d2d2" }

[soldeer]
remappings_version = false
recursive_deps = true
```

Notes:

- `solc = "0.8.27"` is the minimum recommended value. Existing projects may use a newer compiler, but not a version below `0.8.27`.
- `evm_version = "cancun"` is the minimum recommended EVM version. Existing projects may use a newer EVM version, but not a version below `cancun`.
- `optimizer_runs = 800` is a recommended starting point; if the project already has a clear gas or bytecode policy, follow the project configuration.
- If deployment scripts use `vm.writeJson` or write ABI/address files, add the smallest necessary `fs_permissions` entries under `[profile.default]`, for example `{ access = "read-write", path = "./deployments" }` and the frontend contract configuration directory.
- If the project uses standard OpenZeppelin contracts, add them explicitly and pin real versions. Do not mix `latest` with handwritten remappings.

## Installation Commands

```bash
forge soldeer install
forge build
forge test -vv
```

Do not default to Foundry's git installation commands for installing `zama-ai/forge-fhevm`. They use the `lib/` dependency layout, which is easy to mix accidentally with Soldeer's `dependencies/`, `soldeer.lock`, and versioned remappings.

## Dependency Roles

- `forge-std`: the Foundry standard library, including `Test`, `Script`, and cheatcode helpers.
- `@fhevm-solidity`: Zama's FHEVM Solidity contract library, including core contract APIs such as `FHE` and `ZamaConfig`.
- `@encrypted-types`: encrypted type definitions such as `euint32` and `externalEuint32`.
- `forge-fhevm`: Foundry-native FHEVM test library, including `FhevmTest`, encryption/decryption helpers, and local cleartext host contracts.
- `@openzeppelin-contracts`: standard OpenZeppelin contracts, such as `Ownable`, `ReentrancyGuard`, and ERC721/ERC20 interfaces.
- `@openzeppelin-contracts-upgradeable`: OpenZeppelin upgradeable contracts; keep this only when the project uses an upgradeable pattern.
- `@openzeppelin-confidential-contracts`: OpenZeppelin confidential contracts, including ERC7984-related interfaces and implementations.

## Remappings

After Soldeer installs dependencies, it creates version-labeled directories under `dependencies/`. Do not guess the version suffixes; write `remappings.txt` from the directories that actually exist after installation.

The recommended workflow is to inspect the installed directories first:

```bash
find dependencies -maxdepth 1 -type d | sort
forge remappings
```

Then write `remappings.txt` using the actual directory names. Template:

```text
@fhevm/host-contracts/=dependencies/forge-fhevm-60864a0/src/fhevm-host/
@fhevm/solidity/=dependencies/@fhevm-solidity-0.11.1/
encrypted-types/=dependencies/@encrypted-types-0.0.4/
forge-fhevm/=dependencies/forge-fhevm-60864a0/src/
forge-std/=dependencies/forge-std-1.16.0/src
```

If dependency versions or the git `rev` change, update all of the following together:

- The `version` and `rev` entries in `foundry.toml`
- `soldeer.lock`
- Every versioned directory path in `remappings.txt`

## Directory Structure

Recommended:

```text
foundry/
├── foundry.toml
├── remappings.txt
├── soldeer.lock
├── src/
├── test/
└── script/
```

Do not use `node_modules` as a Foundry dependency source. Foundry contract dependencies should come from `dependencies/` or, for the fallback path, `lib/`.

## Git Submodule Fallback

Use submodules only when the project cannot use Soldeer. Keep dependency sources consistent; do not maintain both `dependencies/forge-fhevm-*` and `lib/forge-fhevm` in the same project.

```bash
git submodule add https://github.com/zama-ai/forge-fhevm.git lib/forge-fhevm
git submodule add https://github.com/foundry-rs/forge-std.git lib/forge-std
git submodule add https://github.com/OpenZeppelin/openzeppelin-contracts.git lib/openzeppelin-contracts
git submodule add https://github.com/OpenZeppelin/openzeppelin-contracts-upgradeable.git lib/openzeppelin-contracts-upgradeable
git submodule add https://github.com/OpenZeppelin/openzeppelin-confidential-contracts.git lib/openzeppelin-confidential-contracts
git submodule update --init --recursive
```

With the submodule layout, `foundry.toml` usually changes to:

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

Submodule remappings must point to real directories. For example:

```text
forge-fhevm/=lib/forge-fhevm/src/
@fhevm/host-contracts/=lib/forge-fhevm/src/fhevm-host/
forge-std/=lib/forge-std/src/
@openzeppelin-contracts/=lib/openzeppelin-contracts/contracts/
@openzeppelin-contracts-upgradeable/=lib/openzeppelin-contracts-upgradeable/contracts/
@openzeppelin/confidential-contracts/=lib/openzeppelin-confidential-contracts/contracts/
```

If `@fhevm/solidity` and `encrypted-types` were not installed through Soldeer, confirm whether they are vendored by `forge-fhevm` or provide them separately as submodules/local dependencies. Do not copy Soldeer-style `dependencies/...` remappings into a `lib/` project.

## Compilation Troubleshooting

Check these first when compilation fails:

- Whether `solc` is at least `0.8.27`
- Whether `evm_version` is at least `cancun`
- Whether `libs` matches the dependency directory: Soldeer uses `dependencies`, submodules use `lib`
- Whether the version suffixes in `remappings.txt` actually exist
- Whether both `dependencies/forge-fhevm-*` and `lib/forge-fhevm` have been mixed into the same project
- Whether Hardhat `node_modules` imports have been treated as Foundry remappings
- Whether `@fhevm/solidity` and `encrypted-types` come from compatible versions
