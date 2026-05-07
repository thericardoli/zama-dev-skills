# Zama Workflow Map

## Create or Modify a Solidity Contract

Load order:

1. `zama-fhevm-solidity-core`
2. Read only the core references needed for the task:
   - Types and APIs: `references/api.md`
   - Input handling: `references/patterns/encryption.md`
   - Operations: `references/patterns/operations.md`
   - Conditional logic: `references/patterns/branching.md`
   - ACL: `references/patterns/acl.md`
   - Decryption: `references/patterns/decryption.md`

Do not load Hardhat or Foundry unless the user asks for tests/deployment or the repository structure already identifies the framework.

## Hardhat Development

Load order:

1. `zama-fhevm-solidity-core`
2. `zama-hardhat-contract-dev`

Common tasks:

- Write contracts: start with core.
- Write TypeScript tests: then use Hardhat testing references.
- Deploy: use Hardhat deployment references.
- Write tasks: use Hardhat task references.

## Foundry Development

Load order:

1. `zama-fhevm-solidity-core`
2. `zama-foundry-forge-fhevm`

Common tasks:

- Write contracts: start with core.
- Write Forge tests: use Foundry testing references.
- Fuzzing: use Foundry testing references.
- Local cleartext host contracts: use Foundry deployment references.

## Complete dApp or React dApp

Load order:

1. `zama-fullstack-dapp` to define repository organization, runtime choice, contract/SDK/relayer/frontend boundaries, and validation criteria.
2. `zama-fhevm-solidity-core` to understand the contract ABI, handles, ACL, and decryption design.
3. Load `zama-foundry-forge-fhevm` or `zama-hardhat-contract-dev` according to the repository or the user's requested framework.
4. `zama-sdk`
5. Inside `zama-sdk`, select only the relevant React hooks, provider, custom-contract, Node/local, or token references.

Common tasks:

- Complete local SDK dApp: prefer the Foundry/forge-fhevm local cleartext path.
- Hardhat contract + React SDK: explicitly account for the difference between Hardhat mock flows and SDK runtime flows. Use a testnet or a verified SDK-compatible local stack when needed.
- Read encrypted handles: React hooks.
- Submit encrypted input: React hooks or `@zama-fhe/sdk`.
- User decryption: React hooks.
- Local/Sepolia switching: Zama provider/runtime configuration.

## Scripts or CLI Tools

Load order:

1. `zama-fhevm-solidity-core`
2. `zama-sdk`

Common tasks:

- Encrypt input from a Node script.
- Send transactions with viem or ethers.
- Perform public decryption or user decryption.
- Configure a custom relayer or network.

## ERC7984 token

Load order:

1. `zama-fhevm-solidity-core`
2. core `references/patterns/erc7984.md`
3. Select Hardhat or Foundry according to the framework.
4. If there is a frontend, also read `zama-sdk`.

Combinations:

- Token contract: core ERC7984.
- Token tests: Hardhat or Foundry.
- Token UI: `zama-sdk`.
- Wrapper, vesting, or auction flows: core ERC7984 + ACL + branching/decryption.

## Security Review

Load order:

1. `zama-fhevm-security-review`
2. If contract APIs or patterns need confirmation, also read `zama-fhevm-solidity-core`.
3. If the risk comes from testing or deployment, also read the Hardhat or Foundry skill.
4. If the risk comes from UI code or SDK runtime integration, also read `zama-sdk`.

Review focus:

- Whether encrypted input is verified.
- Whether ACL is propagated correctly.
- Whether public decryption is necessary and replay-protected.
- Whether encrypted conditions can fail open.
- Whether there is reorg risk.
- Whether tests cover only mock happy paths.
