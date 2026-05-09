# Foundry Deployment

This file covers only how to deploy FHEVM dApp contracts. The `deploy-local.sh` / `deploy.sh` scripts shipped with `forge-fhevm` deploy a cleartext FHEVM host stack for local or private development chains; do not treat them as Sepolia/mainnet dApp deployment steps.

For real deployments, do not write private keys into `.env` files, scripts, command history, or CI logs. dApp deployment should use the Foundry keystore: store the encrypted keystore with `cast wallet import`, and select the signer with `forge script --account <name>`.

Contracts should inherit `ZamaEthereumConfig`, allowing `@fhevm/solidity` to configure FHEVM host contracts for the active network:

```solidity
import {FHE, euint64, externalEuint64} from "@fhevm/solidity/lib/FHE.sol";
import {ZamaEthereumConfig} from "@fhevm/solidity/config/ZamaConfig.sol";

contract ConfidentialVault is ZamaEthereumConfig {
    mapping(address => euint64) private _balances;

    function deposit(externalEuint64 encryptedAmount, bytes calldata proof) external {
        euint64 amount = FHE.fromExternal(encryptedAmount, proof);
        euint64 next = FHE.add(_balances[msg.sender], amount);
        _balances[msg.sender] = next;
        FHE.allowThis(next);
        FHE.allow(next, msg.sender);
    }
}
```

## Signer / Keystore

Create or import a deployment account:

```bash
cast wallet import zama-sepolia-deployer --interactive
cast wallet list
cast wallet address --account zama-sepolia-deployer
```

`cast wallet import` stores the encrypted keystore under `~/.foundry/keystores` by default. Require the user to enter the private key and keystore password interactively, so the private key never lands in shell history or `.env`.

`.env` should contain only non-secret-key configuration:

```bash
SEPOLIA_RPC_URL=https://...
MAINNET_RPC_URL=https://...
ETHERSCAN_API_KEY=...
DEPLOYER_ACCOUNT=zama-sepolia-deployer
OWNER=0x...
```

Deployment scripts should not read a private key. Let the wallet options on `forge script` handle signing:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import {Script, console2} from "forge-std/Script.sol";
import {ConfidentialVault} from "../src/ConfidentialVault.sol";

contract DeployConfidentialVault is Script {
    function run() external returns (ConfidentialVault vault) {
        address owner = vm.envAddress("OWNER");

        vm.startBroadcast();
        vault = new ConfidentialVault(owner);
        vm.stopBroadcast();

        console2.log("ConfidentialVault", address(vault));
    }
}
```

Key points:

- Do not write `uint256 deployerPk = vm.envUint("PRIVATE_KEY")`.
- Do not use `vm.startBroadcast(deployerPk)` to read an environment private key.
- Constructor parameters such as owner, admin, token, and threshold should come from environment addresses or explicit arguments; do not assume they should default to the deployer.
- For higher security, prefer hardware wallets, multisigs, KMS, or controlled signing workflows on mainnet. Keystores are appropriate for development and lower-to-medium-risk deployment accounts.

## Local

Local deployment has two layers:

1. Materialize the cleartext FHEVM host contracts at their standard addresses on the local chain.
2. Deploy your dApp contract.

Start Anvil:

```bash
anvil --host 127.0.0.1 --port 8545 --chain-id 31337
```

In another terminal, run the local host-stack script from `forge-fhevm`. Soldeer projects usually place it under `dependencies/forge-fhevm-<version>/deploy-local.sh`; submodule projects usually place it under `lib/forge-fhevm/deploy-local.sh`:

```bash
LOCAL_STATE_RPC_NAMESPACE=anvil ./dependencies/forge-fhevm-<version>/deploy-local.sh --anvil-port 8545
```

`LOCAL_STATE_RPC_NAMESPACE=anvil` is important. `deploy-local.sh` uses `cast client` to detect whether the local RPC is Anvil or Hardhat. In some environments, `cast client` returns an empty value, causing `could not detect a supported local RPC backend`. If the task explicitly supports only Anvil, the local wrapper script should set this environment variable directly instead of relying on auto-detection.

Non-default port:

```bash
LOCAL_STATE_RPC_NAMESPACE=anvil ./dependencies/forge-fhevm-<version>/deploy-local.sh --anvil-port 8546
```

Multiple local nodes:

```bash
LOCAL_STATE_RPC_NAMESPACE=anvil ./dependencies/forge-fhevm-<version>/deploy-local.sh --anvil-port 8545 --anvil-port 8546
```

Reuse already built artifacts:

```bash
LOCAL_STATE_RPC_NAMESPACE=anvil ./dependencies/forge-fhevm-<version>/deploy-local.sh --skip-build --anvil-port 8545
```

For fish shells that cannot use the `NAME=value command` form:

```fish
env LOCAL_STATE_RPC_NAMESPACE=anvil ./dependencies/forge-fhevm-<version>/deploy-local.sh --anvil-port 8545
```

If you wrap this as a root-level npm script, prefer a Node wrapper that finds the versioned directory and passes the environment variable to the child process:

```js
import { access, readdir } from "node:fs/promises";
import { constants } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const root = process.cwd();
const dependencies = join(root, "dependencies");

async function executable(path) {
  try {
    await access(path, constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

async function findDeployLocal() {
  for (const entry of await readdir(dependencies, { withFileTypes: true })) {
    if (!entry.isDirectory() || !entry.name.startsWith("forge-fhevm-")) continue;
    const script = join(dependencies, entry.name, "deploy-local.sh");
    if (await executable(script)) return script;
  }
  throw new Error("Run forge soldeer install before local FHEVM deploy.");
}

const script = await findDeployLocal();
const result = spawnSync(script, ["--anvil-port", "8545"], {
  cwd: root,
  stdio: "inherit",
  shell: false,
  env: {
    ...process.env,
    LOCAL_STATE_RPC_NAMESPACE: process.env.LOCAL_STATE_RPC_NAMESPACE ?? "anvil",
  },
});

process.exit(result.status ?? 1);
```

When deploying the dApp, still prefer the keystore. For first-pass local debugging, you may import Anvil's public test private key interactively into a local account:

```bash
cast wallet import local-anvil --interactive

OWNER=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \
forge script script/DeployConfidentialVault.s.sol:DeployConfidentialVault \
  --rpc-url http://127.0.0.1:8545 \
  --account local-anvil \
  --broadcast
```

If a task requires a disposable one-command local demo, root scripts may combine host-stack deployment with dApp deployment and use Anvil's default unlocked account. Real testnet or production deployments should still use the keystore. The README must clearly say to start Anvil first:

```json
{
  "scripts": {
    "anvil": "anvil --host 127.0.0.1 --port 8545 --chain-id 31337",
    "deploy:fhevm": "node scripts/deploy-fhevm-local.mjs",
    "deploy:local": "npm run deploy:fhevm && forge script script/DeployLocal.s.sol:DeployLocal --rpc-url http://127.0.0.1:8545 --broadcast --unlocked --sender 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
  }
}
```

If `DeployLocal.s.sol` writes frontend address files or `deployments/local.json`, `foundry.toml` must permit writes to the target directories. Otherwise `vm.writeJson` can make the script revert after a successful deployment:

```toml
[profile.default]
fs_permissions = [
  { access = "read-write", path = "./frontend/src/contracts" },
  { access = "read-write", path = "./deployments" }
]
```

Local notes:

- `deploy-local.sh` does not need `.env`; it uses the Anvil key, mock gateway, mock KMS signer, and mock input signer by default.
- In fish, `set LOCAL_STATE_RPC_NAMESPACE anvil` creates only a regular shell variable. To pass it to npm/Node/bash child processes, use `set -x LOCAL_STATE_RPC_NAMESPACE anvil` or `env LOCAL_STATE_RPC_NAMESPACE=anvil npm run deploy:local`.
- If Anvil is not running or the port is wrong, `cast client --rpc-url http://127.0.0.1:8545` will fail; fix RPC reachability before debugging FHEVM deployment.
- The script uses local RPC methods such as `setCode` / `setStorageAt` to materialize host contracts at the fixed addresses in `FHEVMHostAddresses.sol`; this is suitable only for local nodes such as Anvil/Hardhat.
- Contract tests that inherit `FhevmTest` do not need `deploy-local.sh` to run first; `super.setUp()` deploys the host contracts inside the Forge test environment.
- Restarting Anvil clears chain state; local deployment addresses used by the frontend must be regenerated and should not be treated as long-lived configuration.
- In the local cleartext stack, encrypted values are actually tracked in plaintext. It cannot prove production privacy.

## Sepolia

When deploying a dApp to Sepolia, do not deploy the `forge-fhevm` host stack first. Use Zama's official Sepolia FHEVM host contracts and relayer configuration. Current official documentation lists Sepolia host addresses including `FHEVM_EXECUTOR_CONTRACT`, `ACL_CONTRACT`, `HCU_LIMIT_CONTRACT`, `KMS_VERIFIER_CONTRACT`, and `INPUT_VERIFIER_CONTRACT`; the relayer is `https://relayer.testnet.zama.org`, and the gateway chain id is `10901`.

Example `.env.sepolia` without a private key:

```bash
SEPOLIA_RPC_URL=https://...
ETHERSCAN_API_KEY=...
DEPLOYER_ACCOUNT=zama-sepolia-deployer
OWNER=0x...
```

Deploy:

```bash
source .env.sepolia

forge script script/DeployConfidentialVault.s.sol:DeployConfidentialVault \
  --rpc-url "$SEPOLIA_RPC_URL" \
  --account "$DEPLOYER_ACCOUNT" \
  --broadcast \
  --verify \
  --etherscan-api-key "$ETHERSCAN_API_KEY"
```

Sepolia notes:

- Confirm that the contract inherits `ZamaEthereumConfig` and that the current `@fhevm/solidity` version supports Sepolia.
- When frontends/scripts encrypt inputs, user, contract, chain id, and relayer config must all match Sepolia.
- Sepolia is a testnet; do not rely on it for real sensitive data or production fund assumptions.
- Do not run `forge-fhevm/deploy-local.sh` on Sepolia. `deploy.sh` is for remote development chains where you deploy your own cleartext FHEVM stack; it is not the standard path for connecting to Zama Sepolia.
- After deployment, verify at least one real encrypted-input transaction and one user-decrypt/public-decrypt flow, not only `forge verify-contract`.

## Mainnet

Mainnet dApp deployment scripts have the same shape as Sepolia scripts, but before release you must confirm that the current official `@fhevm/solidity`, Zama SDK, and Zama docs provide host contracts, gateway, relayer, and audit status for the target mainnet. If dependency source or official docs do not provide mainnet configuration, do not hardcode Sepolia/local addresses and present them as mainnet.

Example `.env.mainnet` without a private key:

```bash
MAINNET_RPC_URL=https://...
ETHERSCAN_API_KEY=...
DEPLOYER_ACCOUNT=zama-mainnet-deployer
OWNER=0x...
```

Deploy:

```bash
source .env.mainnet

forge script script/DeployConfidentialVault.s.sol:DeployConfidentialVault \
  --rpc-url "$MAINNET_RPC_URL" \
  --account "$DEPLOYER_ACCOUNT" \
  --broadcast \
  --verify \
  --etherscan-api-key "$ETHERSCAN_API_KEY"
```

Mainnet notes:

- Prefer hardware wallets, multisigs, or controlled signer workflows. If using a keystore, use a dedicated deployment account and keep its balance minimal.
- Do not commit production private keys to `.env`, scripts, shell history, or CI logs.
- Rehearse deployment nonce, constructor parameters, verification, permission initialization, and pause/owner logic on a mainnet fork.
- Before releasing FHEVM logic, cover ACL failure paths: wrong users cannot decrypt, missing `allowThis` fails, and handles not marked public cannot be publicly decrypted.
- Do not deploy the `forge-fhevm` cleartext host stack to Ethereum mainnet. It is a development tool, and the cleartext executor does not provide production privacy.
- Review every `FHE.makePubliclyDecryptable` call at the product level; public decrypt on mainnet is permanent disclosure.

## Remote Cleartext Host Stack Is Only for Private Development Chains

`forge-fhevm/deploy.sh` deploys cleartext FHEVM host contracts to testnets/private chains and rewrites `FHEVMHostAddresses.sol`. Use it only when you explicitly intend to maintain your own cleartext development network. When connecting to Zama's official Sepolia/mainnet, deploy only your dApp contract.

If you really need to run `deploy.sh`, inspect the currently installed `forge-fhevm/deploy.sh` for its required variables, but do not write any signer private key into a repository-local `.env`. These scripts typically also involve KMS/coprocessor mock signers; those should only be used for disposable private development chains or short-lived environments managed by a secure secret manager.
