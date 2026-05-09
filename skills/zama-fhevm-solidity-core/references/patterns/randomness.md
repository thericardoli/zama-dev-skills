# Development Pattern: Encrypted Randomness

## When to Use

Use `FHE.randE*` to generate on-chain encrypted random values. Suitable use cases include:

- private random game state
- lotteries or matching
- sealed game rounds
- random results that must remain private first and later be user/public decrypted

## Basic Usage

```solidity
ebool coin = FHE.randEbool();
euint8 die = FHE.randEuint8(8);
euint16 number = FHE.randEuint16();
```

Common functions:

- `FHE.randEbool()`
- `FHE.randEuint8()` / `FHE.randEuint8(upperBound)`
- `FHE.randEuint16()` / `FHE.randEuint16(upperBound)`
- `FHE.randEuint32()` / `FHE.randEuint32(upperBound)`
- `FHE.randEuint64()` / `FHE.randEuint64(upperBound)`
- `FHE.randEuint128()` / `FHE.randEuint128(upperBound)`
- `FHE.randEuint256()` / `FHE.randEuint256(upperBound)`

## Transaction Constraint

Random generation needs to update on-chain PRNG state, so it must execute in a transaction and cannot rely on `eth_call`.

```solidity
function roll() external {
    euint8 value = FHE.randEuint8(8);
    _rolls[msg.sender] = value;
    FHE.allowThis(value);
    FHE.allow(value, msg.sender);
}
```

Do not put random functions in read-only `view` getters.

## Bounded Random

The upper bound for bounded randomness should be a power of two, and the result range is `[0, upperBound - 1]`:

```solidity
euint8 r = FHE.randEuint8(32); // 0..31
```

If the product needs a 1..6 die, do not directly use `upperBound = 6`. You can use 8 as the bound and design rejection/mapping logic, but rejection must not leak or break a loop based on an encrypted condition. The simpler approach is to accept 0..7 and define the game as using an eight-sided die.

## ACL

Random values are new handles and must be authorized:

```solidity
_secret = FHE.randEuint32();
FHE.allowThis(_secret);
FHE.allow(_secret, msg.sender);
```

If the value will be revealed publicly later:

```solidity
FHE.makePubliclyDecryptable(_secret);
```

## Commit/Reveal-style Games

Common structure:

1. Generate encrypted randomness in a transaction.
2. Complete encrypted game logic with `FHE.select` or comparisons.
3. Save the encrypted result and authorize the contract.
4. At settlement, public decrypt the required result, verify the proof, and execute the public reward.

## Security and Cost

- Every random call consumes gas/HCU.
- Do not generate large amounts of randomness inside loops unless the cost is acceptable.
- Do not generate randomness and then immediately public decrypt it in the same function expecting a synchronous result. Public decrypt is asynchronous.
