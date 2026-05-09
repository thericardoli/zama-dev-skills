---
name: zama-fhevm-security-review
description: Use for audits, reviews, threat modeling, or fixes involving Zama FHEVM confidential contracts and SDK/frontend integrations. Covers encrypted input proofs, ACL/handle permissions, user/public decryption, async callback replay, silent failures, unchecked encrypted arithmetic, transient allowances, account abstraction/reorg/finality risks, HCU, ERC7984/wrappers, Relayer SDK, React/wagmi, Node services, deployment issues, and testing gaps.
---

# Zama FHEVM Security Review

## When To Use

Use this skill when the user asks you to audit, review, find vulnerabilities, explain risks, add security tests, fix confidential contracts, or inspect frontend/SDK integrations.

This is an FHEVM-specific security workflow. It does not replace a standard Solidity audit. If you find traditional issues such as reentrancy, access control failures, admin-key risk, upgrade risk, ERC20 accounting bugs, oracle issues, DoS, or deployment secrets, report them as well.

## Which Reference To Read First

- For a full project audit or checklist-driven review: read `references/checklist.md`.
- For FHEVM-specific vulnerability patterns: read `references/vulnerability-patterns.md`.
- For a formal review write-up: read `references/report-template.md`.

When you need implementation details or API semantics, combine this skill with:

- Contract APIs and FHE semantics: `zama-fhevm-solidity-core`.
- Hardhat tests, mocks, and Sepolia workflows: `zama-hardhat-contract-dev`.
- Foundry/forge-fhevm workflows: `zama-foundry-forge-fhevm`.
- React, Node, and Relayer SDK integrations: `zama-sdk`.

## Audit Mental Model

FHEVM security is not "the value is encrypted, therefore it is safe." The core model is:

1. **A handle is a capability reference**: the chain stores ciphertext handles; ACLs decide who can compute with, pass, or decrypt them.
2. **Contracts cannot branch directly on encrypted booleans**: comparison results are `ebool`; business logic must use `FHE.select` or an asynchronous decryption design.
3. **Encrypted arithmetic is unchecked by default**: overflows and underflows do not revert like Solidity checked math; they generally wrap.
4. **Public decryption is permanent disclosure semantics**: once `makePubliclyDecryptable` is called, anyone can request the cleartext.
5. **User decryption is an ACL + session/signature flow**: if the frontend can display a value, that does not prove the contract authorization is correct; review both contract grants and SDK signing context.
6. **Mock/local assumptions differ from Sepolia/mainnet assumptions**: mock decryption helpers do not prove production ACL, Relayer, KMS, Gateway, or reorg/finality paths are safe.

## Review Workflow

1. **Identify versions and execution environment**
   - Record versions for `@fhevm/solidity`, the Hardhat/Foundry plugin, `@zama-fhe/sdk`/React SDK, and OpenZeppelin Contracts.
   - Distinguish Hardhat mock, Foundry cleartext/local, Sepolia, and mainnet. Do not treat passing mock-only helpers as a production security proof.

2. **Map privacy boundaries**
   - List values that must remain private, values intended to become public, and boundary-public values such as shield/unwrap amounts, events, and public decryption results.
   - Identify who should be able to user-decrypt each value: owner, recipient, operator, admin, service, or anyone.
   - Mark information whose disclosure is irreversible, such as sealed bids, votes, private keys, coordinates, liquidation prices, or order sizes.

3. **Trace each handle lifecycle**
   - Sources: `FHE.fromExternal`, trivial encryption, randomness, other contract returns, or old storage values.
   - Uses: operations, comparisons, helper calls, storage writes, events, or view returns.
   - Permissions: `allowThis`, `allow`, `allowTransient`, `makePubliclyDecryptable`, `isSenderAllowed`/`isAllowed`.
   - Sinks: user decryption, public decryption, callbacks/finalization, discard, or overwrite.

4. **Check input and context binding**
   - Untrusted user input must use `externalE* + inputProof` and be verified with `FHE.fromExternal`.
   - When the SDK/tests generate encrypted input, the contract address, user/caller address, chain, and parameter order must match the Solidity consumer.
   - If a third-party caller such as a timelock, multisig, relayer, or router submits an encrypted tuple on behalf of a user, there must be additional binding or validation in the intermediary contract. Do not allow arbitrary callers to replay calldata.

5. **Check ACL least privilege**
   - Whenever a persistent storage handle is updated, call `allowThis` if the contract must use it in later transactions.
   - Grant access only to parties that truly need to decrypt or continue computing; review recipients, spenders, operators, callback contracts, and helper contracts separately.
   - Helper contracts must verify that the caller is authorized for handles they consume, especially in fee, router, auction, batcher, and executor flows.
   - Prefer `allowTransient` for cross-contract access needed only in the current transaction; require a clear justification for persistent grants.

6. **Check arithmetic, silent failures, and business invariants**
   - Assess wraparound risk for every `add/sub/mul/div/rem/shl`. Amounts, fees, decimal scaling, liabilities, votes, and bids need explicit bounds strategy.
   - Balance-insufficient, allowance-insufficient, and bid-not-transferred paths must fail closed. If an underlying confidential token returns an effective transferred amount, the application must use the effective amount rather than the requested amount.
   - Do not treat `ebool` as a normal `bool`. If public execution is needed, design an async decryption, proof verification, and one-time finalization flow.

7. **Check public decryption and async finalization**
   - Use `makePubliclyDecryptable` only for data that the product explicitly allows to become public; once exposed, do not keep assuming privacy.
   - `checkSignatures` handles, cleartexts, ABI types, and order must match exactly.
   - Each request must have a request id, owner/recipient, handle(s), deadline, and status. Consume/close the request before external calls or transfers.
   - Callback/finalize flows must prevent replay, duplicate execution, cross-request proof reuse, expired requests, and incorrect caller/Gateway assumptions.

8. **Check reorgs, account abstraction, and transient storage**
   - Do not grant decryption access to high-value secrets in the same finality window as payment or state updates; use two-step authorization and a finality delay.
   - Under Account Abstraction bundling, multiple user operations can share one transaction's transient context; do not assume transient allowances are naturally isolated across AA-composed calls.
   - For FHEVM-sensitive AA flows, verify cleanup strategy or wallet/bundler-level constraints.

9. **Check SDK, frontend, and services**
   - Browsers must not expose private keys, Relayer API keys, server signers, or deployer keys.
   - Backend Relayer/API key/transaction-signing services need key management, nonce/retry handling, and typed-data signing boundaries; the frontend should receive only public configuration.
   - User-decryption session TTL, keypair storage, account/chain changes, disconnect handling, revoke/refresh behavior, zero handles, and stale decrypt results must be handled.
   - Local cleartext/mock runtimes must not be used for Sepolia/mainnet; chain id, Relayer URL, Gateway/ACL/KMS/InputVerifier configuration must match the target network.

10. **Check test quality**
    - Require tests for wrong contract/user input proof, unauthorized user decryption, over-authorized decryption, ACL recipient/operator boundaries, and multi-user cases.
    - Require tests for overflow/underflow, insufficient-balance silent failure, public decryption proof order, replay/finalize-twice, and expired/cancelled requests.
    - Sepolia/mainnet paths should have at least a small real SDK/Relayer smoke test, or a clear explanation of external-resource limits.

## Output Requirements

Security review output should lead with findings, ordered by severity. Each finding should include:

- File and line number.
- Risk description.
- Exploit or misuse scenario.
- Remediation.
- Suggested tests.

If there are no high-severity issues, still document residual risk, trust assumptions, and testing gaps. Do not provide only a "looks good" summary.

## High-Signal Red Flags

- User input is directly wrapped/cast into an encrypted type, or `FHE.asE*` is used for untrusted input.
- A new storage handle is written without `allowThis`, or the path only works in mock tests.
- Long-lived ACL access is granted to helpers/routers/executors, but the helper does not check `isSenderAllowed`.
- `makePubliclyDecryptable` is used on balances, votes, bids, orders, locations, private keys, or other data that should remain private.
- Public-decrypt finalization does not consume the request, or performs transfers/external calls before closing the request.
- Business state is updated from the requested encrypted amount without confirming the effective transferred/debited amount.
- Encrypted arithmetic affects fees, liabilities, bids, vote power, or decimal scaling without a cap/select strategy.
- `execute(address,bytes)`, batchers, relayers, or AA wallets can make arbitrary calls to ACL or protected contracts from a privileged context.
- The frontend keeps showing decrypt results from an old account/chain, or browser bundles contain API keys/private keys.

## Research Basis

- Zama Protocol docs: encrypted inputs, ACL, public/user decryption, supported types, HCU, reorg handling, and Relayer SDK.
- OpenZeppelin: A Developer's Guide to FHEVM Security.
- OpenZeppelin audits: Zama Confidential Fungible Token, Confidential Vesting/Voting, and Confidential Contracts batcher/diff.
