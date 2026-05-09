# Zama Protocol and fhevm-solidity Overview

## What Zama Protocol Is

Zama Protocol is a protocol stack that brings Fully Homomorphic Encryption (FHE) to EVM smart contracts. It allows contracts to compute over encrypted state without decrypting user data, such as encrypted balances, encrypted votes, encrypted bids, encrypted game state, and private business rules.

In a normal EVM, contract state and calldata are public by default. Even if a frontend encrypts data, the contract cannot directly perform meaningful arithmetic or comparisons over ciphertexts. FHEVM's goal is to let Solidity contracts treat encrypted handles as first-class values and use Zama's coprocessor, ACL, and KMS/relayer systems for encrypted computation, permission control, and controlled decryption.

## What fhevm-solidity Solves

`@fhevm/solidity` is the Solidity library contract developers use directly. It mainly provides:

- **Type wrappers**: encrypted types such as `ebool`, `euintXX`, `eaddress`, and `externalEuintXX`.
- **Input verification**: converts externally submitted encrypted inputs into contract-internal computable values with `FHE.fromExternal(input, proof)`.
- **Encrypted computation**: APIs such as `FHE.add`, `FHE.sub`, `FHE.gt`, and `FHE.select`.
- **Permission control**: manages handle usage and decryption permissions with `FHE.allowThis`, `FHE.allow`, `FHE.allowTransient`, and `FHE.makePubliclyDecryptable`.
- **Decryption verification**: public decrypt signature verification, user decrypt authorization, delegation, and related features.
- **Network configuration**: connects contracts to the FHEVM host contracts for the current chain through `ZamaEthereumConfig`.

## Basic Architecture

A typical FHEVM dApp includes:

- Solidity contracts: define encrypted state and business logic with `@fhevm/solidity`.
- FHEVM host contracts: protocol contracts such as ACL, coprocessor/executor, and KMS verifier contracts.
- Relayer / SDK: used by frontends or scripts to generate encrypted inputs, initiate decrypt flows, and handle signatures and proofs.
- Development framework: the Hardhat plugin or forge-fhevm provides mocks, cleartext helpers, local testing, and deployment support.

## Basic Solidity Contract Flow

Contracts do not receive plaintext user inputs directly. A typical flow is:

1. The user or frontend encrypts plaintext into an encrypted input off-chain.
2. The frontend passes the `externalEuintXX handle` and `inputProof` to the contract.
3. The contract verifies the input with `FHE.fromExternal` and obtains an internal `euintXX`.
4. The contract computes in the encrypted domain with `FHE.*` APIs.
5. The contract sets ACL permissions for new handles.
6. The user reads authorized values through user decrypt, or the application performs public decrypt when appropriate.

## Official Repository Entry Points

When you need to confirm versions, APIs, or examples, check these official or core repositories first:

- Zama FHEVM monorepo: `https://github.com/zama-ai/fhevm`
- Solidity library package: `https://www.npmjs.com/package/@fhevm/solidity`
- Hardhat template: `https://github.com/zama-ai/fhevm-hardhat-template`
- Hardhat plugin package: `https://www.npmjs.com/package/@fhevm/hardhat-plugin`
- Foundry testing library: `https://github.com/zama-ai/forge-fhevm`
- Zama SDK: `https://github.com/zama-ai/sdk`
- React template: `https://github.com/zama-ai/fhevm-react-template`
- Mock utilities: `https://github.com/zama-ai/fhevm-mocks`
- OpenZeppelin confidential contracts: `https://github.com/OpenZeppelin/openzeppelin-confidential-contracts`
- Zama Protocol docs: `https://docs.zama.org/protocol`

## Version Strategy During Development

The Zama ecosystem changes quickly. Before writing code, read the actual dependencies from the current project:

```bash
cat package.json
cat foundry.toml
cat remappings.txt
```

Only query npm or GitHub when you need to confirm current published versions:

```bash
npm view @fhevm/solidity version dist-tags --json
npm view @fhevm/hardhat-plugin version dist-tags --json
gh repo view zama-ai/fhevm --json latestRelease,updatedAt,url
```

Do not blindly copy old imports, old mock paths, or old SDK APIs from a tutorial into a new project.
