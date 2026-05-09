# Development Pattern: Reorg Risk and Two-phase ACL

## Problem

After an ACL authorization event enters a block, it can be observed and propagated by gateways/relayers. If the chain reorgs, a transaction that was "already authorized" may not exist on the final chain, but the authorization information may already have leaked sensitive data.

Most ordinary balances or low-value state do not need extra handling. However, if a handle protects a high-value irreversible secret, such as a private key, unlock code, key material, or major auction secret, consider two-phase authorization.

## Not Recommended: One-step Authorization

```solidity
function buySecret() external payable {
    require(msg.value == 1 ether, "price");
    require(!isBought, "sold");
    isBought = true;
    FHE.allow(secret, msg.sender);
}
```

Problem: payment and authorization complete in the same transaction. If a short-term reorg rolls back state, the secret may already have been decrypted by the wrong user.

## Two-phase Authorization

```solidity
euint256 private secret;
bool public isBought;
uint256 public blockWhenBought;
address public buyer;

function buySecret() external payable {
    require(msg.value == 1 ether, "price");
    require(!isBought, "sold");
    isBought = true;
    blockWhenBought = block.number;
    buyer = msg.sender;
}

function requestSecretAccess() external {
    require(isBought, "not bought");
    require(msg.sender == buyer, "not buyer");
    require(block.number > blockWhenBought + 95, "too early");
    FHE.allow(secret, buyer);
}
```

The official documentation discusses 95 slots using the Ethereum worst-case reorg scenario. Choose the concrete waiting period based on the target chain's finality, asset value, and UX tradeoffs.

## When to Use

Use two-phase ACL when:

- the secret cannot be revoked once leaked
- the secret's value is much higher than the UX cost of waiting
- the authorized party is a buyer, winner, or temporary eligible user
- the business can accept a second transaction

It does not need to be the default when:

- the handle is an ordinary user balance and an incorrect authorization has limited or repairable impact
- user experience is the priority and leakage risk is low
- the application already has app-layer finality waiting or backend risk controls

## Testing Suggestions

- Calling `requestSecretAccess` immediately after purchase should revert.
- After enough blocks have passed, the buyer can receive ACL permission.
- Non-buyers cannot request ACL permission.
- Repeated requests should not produce invalid state.
