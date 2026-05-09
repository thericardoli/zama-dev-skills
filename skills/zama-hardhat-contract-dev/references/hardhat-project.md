# Hardhat Project Structure

Use `zama-ai/fhevm-hardhat-template` as the primary reference, then adapt it to the current project's existing structure.

## Directory Layout

```text
contracts/
deploy/
tasks/
test/
types/
hardhat.config.ts
package.json
tsconfig.json
```

Typical responsibilities:

- `contracts/`: FHEVM Solidity contracts.
- `deploy/`: `hardhat-deploy` scripts.
- `tasks/`: interaction, encrypted input, user decrypt, and operational checks.
- `test/`: mock unit tests and Sepolia e2e tests.
- `types/`: TypeChain output.

## Key Dependencies

The current template uses the following dependency set:

- `@fhevm/solidity`
- `@fhevm/hardhat-plugin`
- `@fhevm/mock-utils`
- `@zama-fhe/sdk`
- `hardhat`
- `hardhat-deploy`
- `ethers`
- `@nomicfoundation/hardhat-ethers`
- `@typechain/hardhat`
- `@typechain/ethers-v6`

Read `package.json` and the lockfile first. Do not apply npm latest APIs directly to older projects.

## hardhat.config.ts

The plugin must be enabled:

```ts
import "@fhevm/hardhat-plugin";
import "@nomicfoundation/hardhat-ethers";
import "@nomicfoundation/hardhat-verify";
import "@typechain/hardhat";
import "hardhat-deploy";
import type { HardhatUserConfig } from "hardhat/config";
import { vars } from "hardhat/config";

const LOCAL_MNEMONIC = "test test test test test test test test test test test junk";
const SEPOLIA_RPC_URL = vars.get("SEPOLIA_RPC_URL", "");
const SEPOLIA_MNEMONIC = vars.get("SEPOLIA_MNEMONIC", "");
const ETHERSCAN_API_KEY = vars.get("ETHERSCAN_API_KEY", "");

function liveMnemonicAccounts(mnemonic: string) {
  if (!mnemonic) return [];
  if (mnemonic === LOCAL_MNEMONIC) {
    throw new Error("Refusing to use the public Hardhat test mnemonic on a live network.");
  }
  return { mnemonic, path: "m/44'/60'/0'/0/", count: 10 };
}

const config: HardhatUserConfig = {
  defaultNetwork: "hardhat",
  namedAccounts: {
    deployer: 0,
  },
  networks: {
    hardhat: {
      accounts: { mnemonic: LOCAL_MNEMONIC },
      chainId: 31337,
    },
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337,
    },
    sepolia: {
      accounts: liveMnemonicAccounts(SEPOLIA_MNEMONIC),
      chainId: 11155111,
      url: SEPOLIA_RPC_URL,
    },
  },
  etherscan: {
    apiKey: ETHERSCAN_API_KEY,
  },
  solidity: {
    version: "0.8.27",
    settings: {
      optimizer: { enabled: true, runs: 800 },
      evmVersion: "cancun",
    },
  },
  typechain: {
    outDir: "types",
    target: "ethers-v6",
  },
};

export default config;
```

Notes:

- FHEVM requires the Cancun EVM.
- Local `hardhat` / `localhost` networks may use the public test mnemonic; Sepolia/mainnet must not reuse it.
- Use a dedicated variable for live-network signers, such as `SEPOLIA_MNEMONIC`. Do not write `vars.get("MNEMONIC", LOCAL_MNEMONIC)` and then feed the same mnemonic to both local and Sepolia networks.
- When `SEPOLIA_RPC_URL` or `SEPOLIA_MNEMONIC` is missing, deployment scripts must fail fast. Do not let commands continue with placeholder Infura keys, empty URLs, or the default mnemonic.
- Hardhat vars reduce the risk of accidentally committing `.env`, but they are still local plaintext files. For production deployment, prefer hardware wallets, multisigs, KMS, or managed secret managers.
- If the project already uses `dotenv`, migrate live secrets to Hardhat vars or a managed signer, then run `npx hardhat vars setup`.

## Contract Baseline

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import {FHE, euint64, externalEuint64} from "@fhevm/solidity/lib/FHE.sol";
import {ZamaEthereumConfig} from "@fhevm/solidity/config/ZamaConfig.sol";

contract ConfidentialVault is ZamaEthereumConfig {
    mapping(address => euint64) private _balances;

    function deposit(externalEuint64 amount, bytes calldata proof) external {
        euint64 value = FHE.fromExternal(amount, proof);
        euint64 next = FHE.add(_balances[msg.sender], value);

        _balances[msg.sender] = next;
        FHE.allowThis(next);
        FHE.allow(next, msg.sender);
    }

    function balanceOf(address user) external view returns (euint64) {
        return _balances[user];
    }
}
```

For contract development details, read `zama-fhevm-solidity-core`. This Hardhat skill focuses on configuration, testing, and deployment.

## Common Commands

Prefer the project's existing npm scripts. Common template commands:

```bash
npm install
npm run compile
npm test
npm run chain
npm run deploy:localhost
npm run deploy:sepolia
npm run verify:sepolia
```

After changing a contract ABI:

```bash
npm run compile
npm run typechain
```

If generated types are still stale:

```bash
npm run clean
npm run compile
```
