# Development Pattern: Encrypted Inputs

## When to Use

Use the external encrypted input pattern when a contract function needs to receive private user input. Typical scenarios include:

- confidential token mint/transfer amount
- private voting choices
- sealed-bid auction bids
- private game actions
- private thresholds, addresses, or boolean flags submitted by users

## Two Sources of Encrypted Values

FHEVM contracts commonly use two sources of encrypted values:

1. **Off-chain user input encryption**: the client generates an `externalEuintXX` and `inputProof` off-chain, then the contract verifies them with `FHE.fromExternal`. The exact generation flow depends on the frontend SDK, Hardhat, or Foundry skill.
2. **On-chain trusted value conversion**: the contract converts trusted plaintext constants or deployment parameters into encrypted values with `FHE.asEuintXX(clear)`.

User input must use the first path. Do not use `FHE.asEuintXX` to accept untrusted user input.

## Receiving Encrypted Inputs in Contracts

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {FHE, euint32, externalEuint32} from "@fhevm/solidity/lib/FHE.sol";
import {ZamaEthereumConfig} from "@fhevm/solidity/config/ZamaConfig.sol";

contract ConfidentialCounter is ZamaEthereumConfig {
    euint32 private _count;

    function increment(externalEuint32 encryptedAmount, bytes calldata inputProof) external {
        euint32 amount = FHE.fromExternal(encryptedAmount, inputProof);

        _count = FHE.add(_count, amount);

        FHE.allowThis(_count);
        FHE.allow(_count, msg.sender);
    }

    function getCount() external view returns (euint32) {
        return _count;
    }
}
```

Key points:

- `externalEuint32` is an external handle parameter, not an internal `euint32` that can be computed over directly.
- `inputProof` can cover multiple encrypted inputs in the same transaction.
- `FHE.fromExternal` is the verification boundary. All user input should enter the encrypted domain here.
- After verification, `amount` can be passed to APIs such as `FHE.add`, `FHE.sub`, and `FHE.select`.

## Multiple Encrypted Inputs

Multiple inputs can be packed into the same ciphertext/proof. On the contract side, receive multiple `externalE*` values and share one final `bytes inputProof`:

```solidity
function initialize(
    externalEbool inputFlag,
    externalEuint32 inputAmount,
    externalEaddress inputOwner,
    bytes calldata inputProof
) external {
    ebool flag = FHE.fromExternal(inputFlag, inputProof);
    euint32 amount = FHE.fromExternal(inputAmount, inputProof);
    eaddress owner = FHE.fromExternal(inputOwner, inputProof);

    _flag = flag;
    _amount = amount;
    _owner = owner;

    FHE.allowThis(_flag);
    FHE.allowThis(_amount);
    FHE.allowThis(_owner);
    FHE.allow(_flag, msg.sender);
    FHE.allow(_amount, msg.sender);
    FHE.allow(_owner, msg.sender);
}
```

The client must keep handles semantically aligned with the Solidity parameters. The documentation notes that Solidity parameter order does not have to match input construction order exactly, but in practice you should keep them aligned to reduce mismatch risk.

Framework-specific encrypted input generation belongs in the corresponding skill:

- Hardhat: `zama-hardhat-contract-dev`
- Foundry/forge-fhevm: `zama-foundry-forge-fhevm`
- React/wagmi/viem, Node scripts, or lower-level SDK usage: `zama-sdk`

## Trusted Value Conversion

Suitable for initial supply, administrator configuration, and constants:

```solidity
euint64 initial = FHE.asEuint64(1_000);
FHE.allowThis(initial);
FHE.allow(initial, owner);
```

Not suitable:

```solidity
function deposit(uint64 clearAmount) external {
    euint64 amount = FHE.asEuint64(clearAmount); // user plaintext input; privacy is already lost
}
```

Reason: trivial encryption only converts plaintext into a ciphertext form compatible with FHE operations. The plaintext has already been exposed in calldata or contract state changes, so it does not provide input privacy.

## Initialization Checks

State variables default to the zero handle. When you need to distinguish "uninitialized" from "plaintext value is 0", use:

```solidity
if (!FHE.isInitialized(_count)) {
    // first write path
}
```

Do not write `euintXX.unwrap(value) == 0` in business logic. Prefer `FHE.isInitialized`.

## Common Mistakes

- Encrypting for contract A but passing the input to contract B.
- Encrypting for Alice but sending the transaction from Bob.
- Declaring the contract parameter as `bytes32` and skipping `FHE.fromExternal`.
- Forgetting `FHE.allowThis` after updating state.
- Using `FHE.asEuintXX(userInput)` to receive user input that should remain private.
