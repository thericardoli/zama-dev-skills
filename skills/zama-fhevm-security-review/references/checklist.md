# FHEVM Security Checklist

## 0. Baseline Information

- Dependency versions: `@fhevm/solidity`, Hardhat/Foundry plugin, `@zama-fhe/sdk`, React SDK, and OpenZeppelin Contracts.
- Target network: mock/local/Sepolia/mainnet. Record chain id and the source of ACL/KMS/InputVerifier/Gateway/Relayer configuration.
- Whether contracts inherit the correct network configuration, such as `ZamaEthereumConfig`; do not hardcode local/mock host addresses for Sepolia.
- Deployment signer/RPC configuration must fail fast; live networks must not use default mnemonics, placeholder RPC URLs, or empty accounts.

## 1. Privacy Boundary

- Values that must remain private: balances, bids, votes, positions, locations, secrets, and private order sizes.
- Values that are public by design: final results, public tallies, unwrap amounts, and settlement prices.
- Naturally public boundary values: ERC20 approve/transfer amounts, shield amounts, withdraw amounts, event metadata, gas, and timing.
- README/UI copy must explain public boundaries clearly and must not imply that shield/unwrap amounts are private.
- Information that cannot be undisclosed once leaked should have a finality delay or two-phase authorization.

## 2. Encrypted Input

- User input should use `externalEbool`, `externalEaddress`, `externalEuintXX`, and `bytes inputProof`.
- Every untrusted encrypted input should call `FHE.fromExternal(input, inputProof)`.
- Look for `euintXX.wrap(bytes32)`, direct casts, or `FHE.asEuintXX` paths that accept user calldata.
- When SDK/tests generate encrypted input, the contract address and user/caller address must match the final `msg.sender` context.
- If multiple encrypted inputs share one proof, handle indexes, proof order, and parameter meaning must align; if each input has its own proof, each proof must match the corresponding parameter.
- Check third-party caller replay risk: timelocks, routers, relayers, multisigs, and batchers must not let attackers trigger reused tuples.

## 3. ACL And Handle Lifecycle

- After every storage handle update, call `FHE.allowThis(handle)` if the contract will need to compute with it in future transactions.
- If a user needs user-decryption access to a handle, grant `FHE.allow(handle, user)`; verify recipient/operator/spender grants match the business logic.
- Check for over-authorization of owners/admins/services that would let them read user secrets.
- Prefer `FHE.allowTransient` when a helper only needs access during the current transaction.
- If persistent `FHE.allow` is granted to a helper/router/executor, require a clear explanation for why long-lived access is safe.
- Helpers that receive external handles must call `FHE.isSenderAllowed(handle)` or an equivalent check.
- When old handles are replaced, old permissions may still expose historical sensitive values; confirm whether the product accepts that history-readability.
- Check for arbitrary `execute(target,data)` entry points that let a permissioned contract call ACL or transfer handle permissions.

## 4. Arithmetic, Conditions, And Business Invariants

- Check whether `euint` arithmetic can wrap: `add`, `sub`, `mul`, `shl`, decimal scaling, and fee numerators.
- Use encrypted guards plus `FHE.select` for caps, insufficient balances, insufficient allowances, and overflow fallbacks.
- Confirm upper layers understand silent failure: confidential token transfers may return zero/effective amounts, so auctions/orders/vaults must not rely only on requested amounts.
- Check whether `ebool` is incorrectly used as a Solidity `if`/`require` condition or described as a synchronous revert.
- If public variables track backing/liability/supply invariants, ensure they align with confidential accounting.
- Decimals must be explicit: USDC/cUSDC are commonly 6 decimals; if arbitrary decimals are supported, scaling and `uint64` bounds need tests.
- Check whether HCU limits can be exceeded; loops, batching, and deep compositions should split work across transactions or cap batch size.

## 5. User Decryption

- Contracts should grant access only to intended readers; a view function returning a handle is not decryption authorization.
- If delegated user decryption is used, clearly separate delegator, delegate, and contractAddress boundaries; the delegate must not be mistaken for the handle's ACL owner.
- Delegations should have reasonable expirations; permanent delegation, wildcard contractAddress, and backend decryption services need product-level approval and a revocation process.
- Revoke/delegate flows should cover same-block races, expired delegations, wrong contractAddress, multi-contract batch delegation, and recovery after delegate key compromise.
- The frontend should request decryption for the current account, chain, and contractAddress; clear stale results after account or network changes.
- Sessions/keypairs should have TTLs; disconnect/account changes should revoke or refresh access.
- Handle zero/uninitialized handles; avoid treating `0x00` as a real balance or continuing to decrypt it.
- Include tests where unauthorized user decryption fails.
- Batch decryption should account for SDK contract address limits, bit-length limits, and error states.

## 6. Public Decryption / Async Finalization

- Use `FHE.makePubliclyDecryptable` only for data that may be permanently public.
- Requests should record request id, requester, recipient, handles, expected type/order, deadline, and status.
- `FHE.checkSignatures` handles count, order, and cleartext ABI types must match the off-chain `publicDecrypt` input.
- Finalize/callback should consume/close the request before transfers, mint/burn, external calls, or granting permissions.
- Prevent replay: duplicate proof finalization, cross-request proof reuse, and use after cancellation or expiry.
- Restrict or verify caller/Gateway/Relayer assumptions; if anyone may finalize, rely on proof and request state rather than caller trust.
- Failure paths must be recoverable: false predicate, zero debit, expiry, cancellation, and KMS/Relayer liveness failures.

## 7. Reorgs, Finality, And Account Abstraction

- Sensitive secret grants may need finality before `allow`, rather than happening in the same block or a short window after payment.
- Sales of confidential information, sealed auctions, secret locations, private keys, and similar flows should use request -> finality delay -> grant decryption.
- Account Abstraction/bundler flows may share transient allowances; require cleanup or avoid AA aggregation for sensitive paths.
- Do not rely on event order or mempool observation as a security boundary.

## 8. SDK, Relayer, Frontend, And Services

- Frontends should load the Zama SDK/React SDK correctly; chain id, Relayer URL, contract address, and ABI should come from canonical artifacts.
- Browsers must not expose private keys, mnemonics, deployer keys, Relayer API keys, or backend signing credentials.
- Relayer/backend services should own transaction submission, EIP-712 signing, nonce/retry logic, and key management; browsers should not hold long-lived service secrets.
- Local cleartext/mock configuration must be local-only; Sepolia/mainnet must not use a cleartext runtime.
- Registry/wrapper discovery should validate result validity; do not hardcode unverified cToken/wrapper addresses.
- SDK imports must match the installed local version; when wagmi adapter mismatches occur, use a documented fallback rather than patching `node_modules`.
- UI should display loading/error/pending/finalized states; do not show stale plaintext while a transaction is pending.

## 9. Minimum Test Coverage

- Wrong user, wrong contract, wrong proof, wrong handle order.
- Unauthorized decrypt failures; recipient/operator/admin permission boundaries.
- Overflow/underflow, `uint64` max, decimal mismatch, zero amount/address.
- Insufficient-balance silent failure and effective amount.
- Public decryption proof verification, replay, finalize twice, cancel/expired/false predicate.
- Timelock tests for high-value reorg/finality authorization flows.
- HCU/batch size limit tests.
- Sepolia/live configuration fail-fast tests: missing RPC/signer should fail clearly.

## 10. Severity Guide

- Critical: unauthorized decryption of core secrets, replayed public decrypt proof draining assets, arbitrary executor transferring ACL, or direct admin/attacker theft of backing funds.
- High: silent failure breaking auction/liquidation/withdrawal invariants, overflow causing systemic undercharging or over-minting, or incorrect recipient grants leaking sensitive balances.
- Medium: production path unusable or DoS-prone, session/chain mixups causing incorrect display, registry/wrapper misconfiguration, or user-triggerable HCU exhaustion.
- Low: misleading privacy-boundary documentation, tests covering only mock happy paths, confusing events/getters, gas issues, or maintainability concerns.
