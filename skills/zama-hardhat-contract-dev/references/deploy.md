# Hardhat Deployment

This document covers only FHEVM dApp contract deployment. The Hardhat plugin prepares FHEVM host contracts on mock networks; Sepolia uses Zama's official FHEVM network configuration.

## Keys and Variables

Do not write private keys into `.env`, scripts, or CI logs. The template uses Hardhat vars:

```bash
npx hardhat vars set SEPOLIA_MNEMONIC
npx hardhat vars set SEPOLIA_RPC_URL
npx hardhat vars set ETHERSCAN_API_KEY
npx hardhat vars setup
```

Note: Hardhat vars live outside the project source tree and help avoid committing secrets, but they are not an encrypted keystore. For production deployments, prefer hardware wallets, multisigs, KMS, or managed secret managers.

`hardhat.config.ts` may use a fixed test mnemonic for local networks, but live networks must use independent variables and must not have a default signer:

```ts
import { vars } from "hardhat/config";

const LOCAL_MNEMONIC = "test test test test test test test test test test test junk";
const SEPOLIA_RPC_URL = vars.get("SEPOLIA_RPC_URL", "");
const SEPOLIA_MNEMONIC = vars.get("SEPOLIA_MNEMONIC", "");

function liveMnemonicAccounts(mnemonic: string) {
  if (!mnemonic) return [];
  if (mnemonic === LOCAL_MNEMONIC) {
    throw new Error("Refusing to use the public Hardhat test mnemonic on a live network.");
  }
  return { mnemonic, path: "m/44'/60'/0'/0/", count: 10 };
}

// hardhat: { accounts: { mnemonic: LOCAL_MNEMONIC } }
// sepolia: { url: SEPOLIA_RPC_URL, accounts: liveMnemonicAccounts(SEPOLIA_MNEMONIC) }
```

Do not write:

```ts
const PRIVATE_KEY = process.env.PRIVATE_KEY;
const MNEMONIC = vars.get("MNEMONIC", LOCAL_MNEMONIC);
// Then use the same MNEMONIC for both hardhat and sepolia
```

Live deployment scripts should also check configuration explicitly as the first step and fail with clear errors instead of waiting for ambiguous RPC or signer failures.

## Deployment Script

`deploy/001_deploy_vault.ts`:

```ts
import { vars } from "hardhat/config";
import type { DeployFunction } from "hardhat-deploy/types";
import type { HardhatRuntimeEnvironment } from "hardhat/types";

const LOCAL_MNEMONIC = "test test test test test test test test test test test junk";

function requireVar(name: string): string {
  const value = vars.get(name, "");
  if (!value) throw new Error(`Missing Hardhat var ${name}. Run: npx hardhat vars set ${name}`);
  return value;
}

function assertLiveNetworkConfig(hre: HardhatRuntimeEnvironment) {
  if (hre.network.name === "sepolia") {
    requireVar("SEPOLIA_RPC_URL");
    const mnemonic = requireVar("SEPOLIA_MNEMONIC");
    if (mnemonic === LOCAL_MNEMONIC) {
      throw new Error("Refusing to deploy Sepolia with the public Hardhat test mnemonic.");
    }
  }
}

const func: DeployFunction = async function (hre: HardhatRuntimeEnvironment) {
  assertLiveNetworkConfig(hre);

  const { deployer } = await hre.getNamedAccounts();
  const { deploy } = hre.deployments;

  const deployed = await deploy("ConfidentialVault", {
    from: deployer,
    args: [],
    log: true,
  });

  console.log("ConfidentialVault", deployed.address);
};

export default func;
func.id = "deploy_confidential_vault";
func.tags = ["ConfidentialVault"];
```

If the constructor requires parameters such as owner, token, or threshold, read them explicitly from Hardhat vars, deployment parameters, or network config. Do not reuse the deployer by default.

## Localhost mock

Terminal 1:

```bash
pnpm run chain
```

Terminal 2:

```bash
pnpm run deploy:localhost
# or
npx hardhat deploy --network localhost
```

Local interaction:

```bash
npx hardhat --network localhost task:deposit --address 0x... --amount 100
npx hardhat --network localhost task:decrypt-balance --address 0x...
```

Notes:

- `npx hardhat test` initializes the FHEVM host inside the in-memory mock network; you do not need to start a node first.
- `npx hardhat node` provides persistent mock state and is useful for frontend or task integration testing.
- Mock mode does not provide production privacy guarantees.

## Sepolia

Sepolia uses real FHEVM encryption and the Zama relayer. Do not run mock-only assertions there.

Prerequisites:

```bash
npx hardhat vars set SEPOLIA_MNEMONIC
npx hardhat vars set SEPOLIA_RPC_URL
npx hardhat vars set ETHERSCAN_API_KEY
```

Deploy:

```bash
npx hardhat deploy --network sepolia
npx hardhat verify --network sepolia <CONTRACT_ADDRESS>
```

Post-deployment checks:

```bash
npx hardhat --network sepolia fhevm check-fhevm-compatibility --address <CONTRACT_ADDRESS>
npx hardhat test --network sepolia
```

Sepolia notes:

- Confirm the contract inherits `ZamaEthereumConfig`.
- Deployment commands must fail clearly when `SEPOLIA_RPC_URL`, `SEPOLIA_MNEMONIC`, or managed signer configuration is missing.
- Do not use the public Hardhat test mnemonic, placeholder RPC URLs, or empty accounts as Sepolia fallbacks.
- Confirm that the contract address, user address, chain ID, and relayer config used by frontend/task encrypted input generation all match Sepolia.
- Sepolia e2e tests are slow; configure longer test timeouts.
- Do not run mock-only `fhevm.debugger.decrypt*` assertions or `fhevm.isMock` suites directly on Sepolia.

## Mainnet

Mainnet deployment is similar to Sepolia, but first confirm that the current `@fhevm/solidity`, `@fhevm/hardhat-plugin`, Zama SDK, and Zama docs support the target mainnet. The plugin README states that mainnet encrypted input / decrypt requires a Zama API key:

```bash
npx hardhat vars set ZAMA_FHEVM_API_KEY
npx hardhat vars get ZAMA_FHEVM_API_KEY
```

Mainnet notes:

- Use a hardware wallet, multisig, or managed signer; do not put production mnemonics/private keys in `.env`.
- Rehearse deployment, verification, constructor arguments, and owner/pause initialization on a fork or Sepolia.
- Perform a product-level review of every `FHE.makePubliclyDecryptable` call.
- After deployment, run the smallest real workflow: encrypted input transaction, user decrypt, and public decrypt if required.
- If the current dependencies do not provide mainnet host config, do not hard-code Sepolia/local addresses and pretend they are mainnet.
