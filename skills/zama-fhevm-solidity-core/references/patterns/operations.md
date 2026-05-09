# Development Pattern: Encrypted Operations

## When to Use

Read this file when a task involves encrypted arithmetic, comparisons, bit operations, type conversion, overflow control, or gas/HCU optimization.

## Type Selection

Prefer the smallest encrypted type that covers the business range:

- Small enums, percentages, levels: `euint8`
- Counters or small point balances: `euint32` or `euint64`
- Token amounts: commonly `euint64`, depending on protocol or library requirements
- Large integers or key material: `euint128` or `euint256`
- Private addresses: `eaddress`
- Private conditions: `ebool`

Do not default to `euint256`. Encrypted operations are expensive, and larger types cost more.

## Arithmetic

Common operations:

```solidity
euint64 c = FHE.add(a, b);
euint64 d = FHE.sub(a, b);
euint64 e = FHE.mul(a, b);
euint64 q = FHE.div(a, 10);
euint64 r = FHE.rem(a, 10);
```

Notes:

- The rhs for `div` and `rem` should usually be a plaintext scalar.
- Encrypted integer arithmetic is unchecked. Overflow and underflow do not automatically revert like ordinary Solidity 0.8 integers.
- Contracts cannot directly obtain a normal `bool` from an encrypted comparison to revert.

## Prefer Scalars

When the same logic can use a plaintext scalar, avoid trivial encryption first:

```solidity
// Worse: constructs one extra encrypted value
x = FHE.add(x, FHE.asEuint32(42));

// Better: uses the scalar overload
x = FHE.add(x, 42);
```

This assumes the scalar itself does not need to remain private.

## Overflow-safe Mint/Update

When updating encrypted total supply or balances, use comparisons and `FHE.select` to make the update fail closed:

```solidity
function mint(externalEuint32 encryptedAmount, bytes calldata inputProof) external {
    euint32 amount = FHE.fromExternal(encryptedAmount, inputProof);

    euint32 nextSupply = FHE.add(totalSupply, amount);
    ebool overflow = FHE.lt(nextSupply, totalSupply);

    totalSupply = FHE.select(overflow, totalSupply, nextSupply);

    euint32 nextBalance = FHE.add(balances[msg.sender], amount);
    balances[msg.sender] = FHE.select(overflow, balances[msg.sender], nextBalance);

    FHE.allowThis(totalSupply);
    FHE.allowThis(balances[msg.sender]);
    FHE.allow(balances[msg.sender], msg.sender);
}
```

This pattern does not revert. Instead, it keeps old state when overflow occurs. The frontend can give users feedback through an encrypted error code or through public/user-decrypted state.

## Comparisons and Min/Max

```solidity
ebool enough = FHE.ge(balance, amount);
euint64 smaller = FHE.min(a, b);
euint64 larger = FHE.max(a, b);
```

`ebool` is an encrypted condition. It can only continue participating in FHE operations or `FHE.select`; it cannot be written as:

```solidity
if (enough) {
    // invalid
}
```

## Conditional Updates

Keep the old balance when funds are insufficient:

```solidity
ebool canSpend = FHE.ge(balance, amount);
euint64 spend = FHE.select(canSpend, amount, FHE.asEuint64(0));

balances[from] = FHE.sub(balance, spend);
balances[to] = FHE.add(balances[to], spend);
```

## Casting and Trivial Encryption

Convert trusted plaintext to encrypted values:

```solidity
euint64 publicAmount = FHE.asEuint64(100);
ebool flag = FHE.asEbool(true);
eaddress account = FHE.asEaddress(msg.sender);
```

Type conversion:

```solidity
euint64 wide = FHE.asEuint64(narrow32);
euint32 truncated = FHE.asEuint32(wide);
```

Widening preserves information. Narrowing may truncate. The plaintext used for trivial encryption is still public; do not use it to protect user-private input.

## Bit Operations

Useful for bitmaps, masked flags, and low-level protocol state:

```solidity
euint32 masked = FHE.and(value, 0xff);
euint32 shifted = FHE.shr(value, 8);
euint32 rotated = FHE.rotl(value, 3);
```

Shift/rotate counts may be taken modulo the target bit width. Check the current `FHE.sol` when exact semantics matter.

## Authorize Results

After every operation that produces a new handle, set ACL permissions again:

```solidity
result = FHE.add(a, b);
FHE.allowThis(result);
FHE.allow(result, msg.sender);
```

Do not assume permissions on input handles automatically propagate to long-lived permissions on output handles.
