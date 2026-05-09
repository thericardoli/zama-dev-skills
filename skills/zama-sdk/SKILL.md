---
name: zama-sdk
description: Use this when a TypeScript application needs to interact with Zama FHEVM/confidential contracts. Covers browser and React dApps with @zama-fhe/sdk and @zama-fhe/react-sdk, wagmi/viem/ethers wallet integration, Node scripts or backend services, local cleartext development, relayer configuration, encrypted inputs, user/public/delegated decryption, and ERC7984 confidential token workflows.
---

# Zama SDK

`@zama-fhe/sdk` and `@zama-fhe/react-sdk` are the TypeScript SDKs for integrating Zama Protocol FHEVM / confidential smart contracts at the application layer. They cover browser dApps, React/wagmi frontends, Node.js scripts or backends, local cleartext development, and common ERC7984 confidential token product flows.

Official GitHub repository: `https://github.com/zama-ai/sdk`

## Included Content

This skill primarily organizes the following topics:

- SDK initialization: relayer runtime, signer, storage, and network transport.
- React integration: `ZamaProvider`, wagmi, TanStack Query hooks, and Next.js client/server boundaries.
- Custom FHE contracts: encrypted inputs, input proofs, contract writes, user decryption, and public decryption.
- ERC7984 tokens: shield, confidential balances, confidential transfers, operator approvals, unshield, and registry discovery.
- Node and local development: `RelayerNode`, request-scoped storage, proxies, and `RelayerCleartext`.
- Product integration: activity feeds, wallet/exchange displays, delegated decryption, typed errors, and troubleshooting.

## How to Use

1. First decide whether you are implementing an ERC7984 token flow or a custom FHE contract flow.
2. Then identify the runtime environment: React/browser, vanilla TypeScript, Node backend/script, or local cleartext.
3. Choose the reference for that environment, set up the SDK/Provider first, then implement the specific business action.
4. When an API name or parameter shape is uncertain, check `references/api-reference.md`, then inspect the installed `node_modules/@zama-fhe/*` types in the target project.

## Reference Index

| File | When to Read |
| --- | --- |
| `references/getting-started.md` | First integration in a new project; quickly understand what the SDK does, which packages to install, and how to write minimal React/Node/local examples. |
| `references/configuration.md` | Configure relayers, network presets, API keys, backend proxies, signers, storage, registry overrides, and artifact caching. |
| `references/session-security.md` | Handle wallet signature prompts, decrypt credentials, TTLs, session lifecycle, browser security, and API key boundaries. |
| `references/custom-contracts.md` | The target contract is not an ERC7984 token, but custom encrypted state such as auctions, vaults, counters, or voting. |
| `references/react-wagmi-nextjs.md` | React, wagmi, or Next.js projects that need provider wiring, hooks, authorization gates, and SSR/client boundaries. |
| `references/node-and-local.md` | Node scripts, backend services, server-side relayer auth, request isolation, and local cleartext runtime. |
| `references/token-workflows.md` | ERC7984 confidential token shield, balance, transfer, approve, unshield, registry, and token hooks. |
| `references/activity-wallet-integration.md` | Wallets, portfolios, exchanges, or dashboards that need activity feeds, wrapper discovery, and operator/delegation UX. |
| `references/errors-events.md` | Typed error handling, `matchZamaError`, SDK lifecycle events, event decoders, and activity helpers. |
| `references/api-reference.md` | Look up import paths, class/hook names, parameter shapes, query factories, and local type entry points. |
| `references/troubleshooting.md` | Debug import, worker/WASM, relayer auth, decrypt, token balance, registry, and cleartext issues. |

## Workflow

1. First read the target project's `package.json`, lockfile, Node version, framework, and wallet stack.
2. Pick the most relevant reference from the index above; there is no need to read the full documentation set end to end.
3. Choose the runtime by environment: use `RelayerWeb` for browser/React, `RelayerNode` for Node backends/scripts, and `RelayerCleartext` for local cleartext.
4. For new projects, query the real published `@zama-fhe/sdk` / `@zama-fhe/react-sdk` versions from the pnpm registry instead of copying stale versions.
5. Choose the signer by wallet stack: try `WagmiSigner` first for wagmi; if the current SDK/wagmi combination fails to build, immediately switch to the custom `GenericSigner` fallback in this skill; use `ViemSigner` for viem and `EthersSigner` for ethers.
6. Choose storage by data lifecycle: `indexedDBStorage` for browsers, `memoryStorage` for tests or one-off scripts, and `asyncLocalStorage` for request isolation in Node.
7. Set up the SDK/Provider before implementing business flows; avoid mixing network configuration, wallet state, contract ABIs, and UI state in the same step.
8. Split token tasks into shield, balance, transfer, operator approval, unshield, and activity feed work; route custom contract tasks through the encrypt/decrypt documentation.
9. Finally check contract address, user address, chain id, handle, input proof, ACL, API key exposure, session TTL, browser security headers, and SSR boundaries.
