# Development Pattern: Branching, Loops, and Error Handling

## Core Limitation

Encrypted comparisons return `ebool`. An `ebool` cannot drive Solidity `if`, `while`, `require`, or `revert`, because that would require the chain to know the plaintext condition.

Incorrect:

```solidity
ebool canTransfer = FHE.ge(balance, amount);
if (canTransfer) {
    // invalid
}
```

Correct approaches:

- Use `FHE.select` for conditional updates inside the encrypted domain.
- If ordinary Solidity branching is required, public decrypt first and continue through an asynchronous finalize step.

## Conditional Assignment with FHE.select

```solidity
ebool isAbove = FHE.lt(highestBid, bid);
highestBid = FHE.select(isAbove, bid, highestBid);
winningAddress = FHE.select(isAbove, FHE.asEaddress(msg.sender), winningAddress);

FHE.allowThis(highestBid);
FHE.allowThis(winningAddress);
```

`FHE.select(condition, valueIfTrue, valueIfFalse)` produces a new encrypted handle. Even if the plaintext result equals the old value, reconsider ACL permissions.

## Fail-closed Business Updates

Do not revert when the balance is insufficient. Instead, set the moved amount to 0:

```solidity
function _transfer(address from, address to, euint64 amount) internal {
    ebool canTransfer = FHE.ge(_balances[from], amount);
    euint64 moved = FHE.select(canTransfer, amount, FHE.asEuint64(0));

    _balances[from] = FHE.sub(_balances[from], moved);
    _balances[to] = FHE.add(_balances[to], moved);

    FHE.allowThis(_balances[from]);
    FHE.allowThis(_balances[to]);
    FHE.allow(_balances[from], from);
    FHE.allow(_balances[to], to);
}
```

If users need to know why an operation failed, pair this with an encrypted error code.

## Encrypted Error Code

Encrypted condition failures do not automatically revert. You can record the latest error per user:

```solidity
struct LastError {
    euint8 code;
    uint256 timestamp;
}

euint8 internal NO_ERROR;
euint8 internal NOT_ENOUGH_FUNDS;
mapping(address => LastError) private _lastErrors;

event ErrorChanged(address indexed user);

constructor() {
    NO_ERROR = FHE.asEuint8(0);
    NOT_ENOUGH_FUNDS = FHE.asEuint8(1);
    FHE.allowThis(NO_ERROR);
    FHE.allowThis(NOT_ENOUGH_FUNDS);
}

function _setLastError(address user, euint8 code) internal {
    _lastErrors[user] = LastError(code, block.timestamp);
    FHE.allowThis(code);
    FHE.allow(code, user);
    emit ErrorChanged(user);
}
```

In business logic:

```solidity
ebool ok = FHE.ge(balance, amount);
_setLastError(msg.sender, FHE.select(ok, NO_ERROR, NOT_ENOUGH_FUNDS));
```

Encrypted constants that will be reused across future transactions also need persistent permission for the contract itself during initialization.

The frontend listens for `ErrorChanged`, reads the handle, then user decrypts it.

## Fixed-count Loops

Do not use an encrypted condition to break a loop:

```solidity
while (FHE.lt(x, maxValue)) {
    // invalid
}
```

Use a fixed-count loop with a public upper bound:

```solidity
for (uint256 i = 0; i < 10; i++) {
    euint8 shouldAdd = FHE.select(FHE.lt(x, maxValue), FHE.asEuint8(2), FHE.asEuint8(0));
    x = FHE.add(x, shouldAdd);
}
```

The fixed iteration bound must have acceptable gas/HCU cost. If the bound is large, redesign the product logic.

## Avoid Encrypted Indexes

Selecting an array element by encrypted index is usually expensive. To hide the index, you must iterate over all elements and aggregate with `FHE.select`:

```solidity
euint32 selected = FHE.asEuint32(0);
for (uint256 i = 0; i < items.length; i++) {
    ebool matchIndex = FHE.eq(encryptedIndex, FHE.asEuint32(uint32(i)));
    selected = FHE.select(matchIndex, items[i], selected);
}
```

Avoid this pattern unless the array is very small.

## Asynchronous Public Branching

If ordinary Solidity logic must depend on an encrypted result, such as "the winner claims an NFT", split the flow:

1. Encrypted logic computes `winningAddress`.
2. After the auction ends, call `makePubliclyDecryptable(winningAddress)` and emit a request.
3. Off-chain public decrypt runs.
4. `finalize` verifies the proof and writes public `winnerAddress`.
5. Later ordinary `require(msg.sender == winnerAddress)` branches can run.

This is the basic structure for sealed-bid auction applications.
