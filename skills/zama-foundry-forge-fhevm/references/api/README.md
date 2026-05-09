# forge-fhevm API Guide

## API Layers

Most tests only need the first layer:

| Layer | File to read | When to use it |
| --- | --- | --- |
| Standard tests | `fhevm-test.md` | Writing `FhevmTest`, `encryptUint64`, `decrypt`, `userDecrypt`, and `publicDecrypt` tests |
| Custom input proofs | `input-proof-helper.md` | When you need to assemble an input proof yourself instead of using `encrypt*` |
| Custom KMS proofs | `kms-decryption-proof-helper.md` | When you need direct control over the cleartext encoding passed to `FHE.checkSignatures` |
| Custom user-decrypt signatures | `user-decrypt-helper.md` | When you need to manually verify or generate the user-decrypt EIP-712 digest |

## Recommended Reading Order

1. For standard application tests, read only `fhevm-test.md`.
2. If the public decrypt callback is complex, read `kms-decryption-proof-helper.md`.
3. If the encrypted input proof contains more than one handle, read `input-proof-helper.md`.
4. If user-decrypt signatures must align with a frontend or SDK, read `user-decrypt-helper.md`.

## Critical Boundaries

- `decrypt` is a test backdoor: it only reads the local plaintext database and does not check ACL.
- `publicDecrypt` checks the public-decrypt flag and returns a KMS-style proof.
- `userDecrypt` checks persistent ACL for both the user and contract, then verifies the user signature.
- `buildDecryptionProof` only builds a KMS proof; it does not check ACL or prove that public disclosure is allowed by the application.
- `signUserDecrypt` only builds the user signature; it does not grant handle permissions. Authorization must come from `FHE.allowThis` and `FHE.allow` in the contract.

## Source of Truth

API documentation can lag behind the source. When developing or fixing tests, confirm behavior in this order:

1. The `forge-fhevm/FhevmTest.sol` or helper source targeted by the current project's remapping.
2. The installed `forge-fhevm` dependency's `docs/api/*.md`.
3. The notes in this directory.
