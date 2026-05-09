# Development Pattern: Decryption

## Choosing a Decryption Path

FHEVM commonly has three read paths:

- **No decryption**: continue computing in the encrypted domain. Prefer this when possible.
- **User decrypt**: only authorized users see the plaintext off-chain.
- **Public decrypt**: the result is public and anyone can obtain the plaintext. If needed, verify KMS signatures on-chain before continuing public business logic.

Default to user decrypt. Use public decrypt only when the result is meant to be public.

## User decrypt

User decrypt is suitable when users need to read encrypted handles they are authorized for, such as balances, counters, or private voting state.

Contract-side requirements:

```solidity
FHE.allowThis(value);
FHE.allow(value, user);
```

Both are important:

- `allowThis` lets the dApp contract participate in the user decrypt authorization path and allows later computation.
- `allow(value, user)` allows the specified user to decrypt the handle.

Example:

```solidity
function setValue(externalEuint32 input, bytes calldata proof) external {
    euint32 value = FHE.fromExternal(input, proof);
    _value = value;
    FHE.allowThis(_value);
    FHE.allow(_value, msg.sender);
}

function valueHandle() external view returns (euint32) {
    return _value;
}
```

For multi-value user decrypt, authorize both the contract itself and the user for every handle:

```solidity
FHE.allowThis(_encryptedBool);
FHE.allowThis(_encryptedAmount);
FHE.allowThis(_encryptedAddress);

FHE.allow(_encryptedBool, msg.sender);
FHE.allow(_encryptedAmount, msg.sender);
FHE.allow(_encryptedAddress, msg.sender);
```

The exact off-chain user decrypt call belongs to the frontend SDK, Hardhat, or Foundry skill. Solidity core only requires the contract to store handles correctly and grant ACL permissions.

## Contract Design Notes for User Decrypt

- Getters return encrypted handles, not plaintext.
- Grant `FHE.allow` only to people who are allowed to know the value according to the business logic.
- If a recipient needs to read the balance they received, authorize the recipient during transfer.
- If an operator only needs temporary on-chain use, prefer `allowTransient` over long-lived `allow`.
- Frontends should handle zero or uninitialized handles to avoid meaningless decrypt requests.

## Public decrypt

Public decrypt is suitable for results everyone is allowed to know, such as final vote counts, the winning price after an auction ends, or public game-round results.

First mark the value on-chain:

```solidity
FHE.makePubliclyDecryptable(result);
```

Typical three-step flow:

1. Run confidential logic on-chain to produce an encrypted result.
2. Call an on-chain request function that marks the result as publicly decryptable and emits the handle.
3. The off-chain relayer/SDK performs public decrypt. The on-chain callback/finalize function verifies the proof with `FHE.checkSignatures` and then writes public state.

If the decrypted result is consumed on-chain, KMS signatures must be verified:

```solidity
bytes32[] memory handles = new bytes32[](1);
handles[0] = FHE.toBytes32(result);

FHE.checkSignatures(handles, abi.encode(cleartexts), decryptionProof);
```

Production contracts should bind state such as request id, expected handles, callback caller, and whether the result has already been consumed to prevent replay and mismatches.

For multi-value public decrypt, the handle order, `abi.encode(...)` order, and SDK public decrypt input order must match exactly:

```solidity
bytes32[] memory handles = new bytes32[](2);
handles[0] = FHE.toBytes32(_encryptedFoo);
handles[1] = FHE.toBytes32(_encryptedBar);

bytes memory encoded = abi.encode(clearFoo, clearBar);
FHE.checkSignatures(handles, encoded, proof);
```

If the order is wrong, verification should fail even if the proof came from the real KMS.

## Public Decrypt Finalize Template

```solidity
bool private _requested;
bool private _finalized;
eaddress private _winner;
address public winner;

event WinnerDecryptionRequested(eaddress winnerHandle);

function requestWinnerDecryption() external {
    require(!_requested, "already requested");
    _requested = true;
    FHE.makePubliclyDecryptable(_winner);
    emit WinnerDecryptionRequested(_winner);
}

function finalizeWinner(bytes memory clearResult, bytes memory proof) external {
    require(_requested, "not requested");
    require(!_finalized, "already finalized");

    bytes32[] memory handles = new bytes32[](1);
    handles[0] = FHE.toBytes32(_winner);
    FHE.checkSignatures(handles, clearResult, proof);

    winner = abi.decode(clearResult, (address));
    _finalized = true;
}
```

Add caller checks, request ids, deadlines, expected handle hashes, and similar constraints according to the business logic.

## Cases That Do Not Need Decryption

Prefer completing business logic inside the encrypted domain:

```solidity
ebool canSpend = FHE.ge(balance, amount);
euint64 next = FHE.select(canSpend, FHE.sub(balance, amount), balance);
```

Do not public decrypt a private value just to run an `if` branch.

## Common Mistakes

- Forgetting `FHE.allowThis`, which causes user decrypt to fail.
- Authorizing only `msg.sender` when the recipient also needs to decrypt.
- Calling `makePubliclyDecryptable` on sensitive balances or orders.
- Not checking request id or handles in a public decrypt callback.
- Starting user decrypt from the frontend for a zero handle.
- Using a different handle order and ABI encoding order for multi-value public decrypt.
- Missing replay protection in finalize functions, allowing the same proof to be consumed repeatedly.
