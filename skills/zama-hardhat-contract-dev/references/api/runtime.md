# Runtime API

`@fhevm/hardhat-plugin` extends the Hardhat Runtime Environment:

```ts
import { fhevm } from "hardhat";
// or
import * as hre from "hardhat";
await hre.fhevm.getRelayerMetadata();
```

`hardhat.config.ts` must include:

```ts
import "@fhevm/hardhat-plugin";
```

## Runtime Mode

```ts
if (!fhevm.isMock) {
  this.skip();
}
```

`fhevm.isMock`:

- `true`: Hardhat in-memory or Hardhat node mock environment; suitable for unit tests and local integration work.
- `false`: real FHEVM environments such as Sepolia/mainnet, using real encryption and the relayer.

## CLI Task Initialization

Custom Hardhat tasks must initialize first:

```ts
task("task:decrypt-balance").setAction(async (_args, hre) => {
  const { fhevm } = hre;
  await fhevm.initializeCLIApi();
});
```

Regular `npx hardhat test` runs are initialized by the plugin and do not require a manual call.

## Configuration Checks

After deploying or connecting to a remote network, check whether the contract uses the correct FHEVM host config:

```ts
await fhevm.assertCoprocessorInitialized(contract, "ConfidentialVault");
const cfg = await fhevm.getCoprocessorConfig(await contract.getAddress());
```

The CLI command is also available:

```bash
npx hardhat --network sepolia fhevm check-fhevm-compatibility --address 0x...
```

## Events and HCU

```ts
const receipt = await tx.wait();
const events = fhevm.parseCoprocessorEvents(receipt?.logs);
const hcu = fhevm.computeTransactionHCU(receipt!);
```

Use these helpers to inspect FHE executor events and estimate the cost of FHE operations. Regular business assertions should not rely on HCU alone.

## Error Troubleshooting

```ts
try {
  await tx.wait();
} catch (e) {
  await fhevm.tryParseFhevmError(e, { encryptedInput, out: "console" });
  throw e;
}
```

Common parseable issues include encrypted input target/user binding mistakes, handle type mismatches, and missing ACL permissions.
