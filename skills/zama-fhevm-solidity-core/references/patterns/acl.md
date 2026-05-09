# Development Pattern: ACL Permission Control

## Core ACL Problem

In FHEVM, receiving the `bytes32` for an encrypted handle is not enough to use it. ACL controls:

- which contracts can continue computing over a handle
- which users can user decrypt a handle
- whether a handle can be public decrypted
- whether a temporary call path can use a handle

Without ACL permissions, a contract cannot continue operating on a handle in future transactions even if it stores the handle. Therefore, every newly generated ciphertext requires a fresh decision about permission propagation.

## Basic Authorization Combination

After saving state, usually grant at least:

```solidity
_balance[user] = nextBalance;
FHE.allowThis(nextBalance);
FHE.allow(nextBalance, user);
```

If a return value is only passed to another contract within the same transaction, use transient authorization:

```solidity
FHE.allowTransient(value, target);
```

If the result should be public:

```solidity
FHE.makePubliclyDecryptable(result);
```

## Chained Syntax

If the project enables `using FHE for *;`, chained authorization is available:

```solidity
using FHE for *;

_value = FHE.add(_value, amount);
_value.allowThis().allow(msg.sender);
```

Chaining is only syntax sugar. When team style is inconsistent, prefer explicit `FHE.allow...` calls to reduce misreads.

## Multi-user Transfer Pattern

```solidity
function transfer(address to, externalEuint64 encryptedAmount, bytes calldata proof) external {
    euint64 amount = FHE.fromExternal(encryptedAmount, proof);

    euint64 senderBalance = _balances[msg.sender];
    euint64 recipientBalance = _balances[to];

    ebool canTransfer = FHE.ge(senderBalance, amount);
    euint64 nextSender = FHE.select(canTransfer, FHE.sub(senderBalance, amount), senderBalance);
    euint64 nextRecipient = FHE.select(canTransfer, FHE.add(recipientBalance, amount), recipientBalance);

    _balances[msg.sender] = nextSender;
    _balances[to] = nextRecipient;

    FHE.allowThis(nextSender);
    FHE.allowThis(nextRecipient);
    FHE.allow(nextSender, msg.sender);
    FHE.allow(nextRecipient, to);
}
```

Note: if the sender also needs to know whether the recipient update succeeded, add authorization or design an event/public state path.

## Sender Authorization Checks for Input Handles

If a function receives an encrypted handle that was not produced by `FHE.fromExternal` in the same call, but instead came from existing state or another contract, check whether the caller is allowed to use that handle:

```solidity
function consumeExisting(euint64 amount) external {
    if (!FHE.isSenderAllowed(amount)) {
        revert UnauthorizedHandle();
    }
    // safe to use amount under current ACL assumptions
}
```

These checks can reduce the attack surface where transaction success or failure leaks information about someone else's private state.

## Checking Permissions

```solidity
if (!FHE.isSenderAllowed(value)) {
    revert Unauthorized();
}

bool aliceAllowed = FHE.isAllowed(value, alice);
```

`isSenderAllowed` is useful for functions where the caller must already be authorized to use the handle.

## Cross-contract Transient Authorization

When passing an encrypted value to another contract for use in the current call:

```solidity
FHE.allowTransient(amount, address(token));
token.confidentialTransferFrom(msg.sender, address(this), amount);
```

This is common in composed contracts such as ERC7984 integrations, auctions, AMMs, vesting, and wrappers. Do not grant an external contract permanent permission unless it truly needs to use the handle across transactions.

## Permission Propagation Strategy

When designing each state variable, answer:

- Who needs to continue participating in on-chain computation?
- Who needs user decrypt?
- Is public decrypt allowed?
- Do recipients, spenders, delegates, or operators need permissions?
- Are permissions on old handles acceptable?

## High-value Secrets and Reorgs

If authorizing a handle to the wrong user would cause irreversible high-value loss, such as leaking private keys, key material, or major auction results, use two-phase authorization: first record purchase or eligibility state, then wait for enough block confirmations before calling `FHE.allow`. See `reorgs.md`.

## Common Mistakes

- Calling only `allow(user)` after updating state and forgetting `allowThis`.
- Giving the owner global decrypt permission when the product does not allow the owner to see user-private values.
- Leaving the recipient unable to decrypt their own balance after a transfer.
- Leaving public decrypt in production code as a debugging convenience.
- Using transient authorization as long-term permission.
- Forgetting `allowTransient` before an external contract call, causing ERC7984 or composed-contract internals to fail.
