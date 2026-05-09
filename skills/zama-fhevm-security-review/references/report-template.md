# FHEVM Security Review Report Template

## Findings

Sort findings by severity. Do not start with a long summary.

### Critical / High / Medium / Low

Use this structure for each finding:

```text
Title: A concise sentence describing the specific issue
Location: contracts/X.sol:123 or packages/frontend/src/Y.tsx:45
Severity: High

Issue:
Explain exactly what the code does wrong. Identify the relevant handle, ACL grant, proof, SDK session, public decryption request, or business invariant.

Impact:
Explain what an attacker or mistaken user can cause, such as unauthorized decryption, repeated withdrawals, winning an auction with an empty transfer, the wrong user seeing plaintext, or Sepolia deployment using a default mnemonic.

Scenario:
List the minimal attack or failure path. For FHEVM issues, explain why mock environments may not reveal the issue and why production paths would.

Remediation:
Provide the smallest actionable fix direction. When relevant, mention `FHE.fromExternal`, `FHE.isSenderAllowed`, `allowTransient`, `FHE.select`, request consumption, finality delay, SDK session cleanup, and similar controls.

Tests:
List tests to add or update, including wrong user/contract proof, unauthorized decryption, replay, wrong handle order, overflow, insufficient-balance silent failure, and live configuration fail-fast behavior.
```

## Trust Assumptions

Briefly list the assumptions the review depends on:

- Target network and FHEVM version.
- KMS/Gateway/Relayer trust and liveness assumptions.
- Whether anyone is allowed to finalize public decryption.
- Which data the product allows to become public.
- Whether Account Abstraction, routers, batchers, or multisigs are supported.
- Whether OpenZeppelin confidential contracts, ERC7984, or the wrapper registry are used.

## Privacy Boundary

Use a table or short list to describe:

- Private: values that must remain private.
- Public by design: values intentionally made public by the business flow.
- Public boundary: ERC20 shield/unwrap, events, and transaction metadata.
- Authorized readers: who may user-decrypt each handle.
- Permanent public decryption: which handles are passed to `makePubliclyDecryptable`, and why.

## Test Gaps

List missing tests specifically; do not merely say "more tests are needed":

- Input proof: wrong user, wrong contract, wrong order, replay.
- ACL: unauthorized decryption failure, recipient/operator permissions, helper permissions.
- Arithmetic: overflow, underflow, `uint64` max, decimal scaling.
- Silent failure: insufficient balance, effective transferred/debited amount.
- Public decryption: proof order, finalize twice, cancelled/expired/false predicate.
- SDK: account/chain switch, zero handle, session expiry, Relayer error.
- Deployment: live network missing signer/RPC fail-fast behavior.

## Positive Notes

List only genuinely valuable security design choices, such as:

- Request is consumed before external calls.
- Helper uses `isSenderAllowed`.
- Public decryption is used only for explicitly public results.
- Live deployment does not use a default mnemonic.
- Frontend does not expose secrets and artifacts are synchronized automatically.

## Summary

End with a 3-5 sentence summary:

- Overall risk level.
- The most important 1-2 fixes.
- Which issues are implementation quality problems and which may stem from skill/docs guidance.
- Recommended next steps: add tests, redesign, run Sepolia smoke tests, or request manual audit.
