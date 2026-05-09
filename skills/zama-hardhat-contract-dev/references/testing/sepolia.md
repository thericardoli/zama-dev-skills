# Sepolia e2e Testing

Sepolia uses real FHEVM encryption. Tests are slow and require test ETH. Keep only a small number of end-to-end paths there; do not move the entire mock unit test suite over.

## Basic Structure

```ts
import { FhevmType } from "@fhevm/hardhat-plugin";
import { expect } from "chai";
import { deployments, ethers, fhevm } from "hardhat";

describe("ConfidentialVaultSepolia", function () {
  before(async function () {
    if (fhevm.isMock) {
      this.skip();
    }
  });

  it("deposits and decrypts", async function () {
    this.timeout(4 * 40_000);

    const [alice] = await ethers.getSigners();
    const deployment = await deployments.get("ConfidentialVault");
    const vault = await ethers.getContractAt("ConfidentialVault", deployment.address);

    const encrypted = await fhevm
      .createEncryptedInput(deployment.address, alice.address)
      .add64(100n)
      .encrypt();

    const tx = await vault.connect(alice).deposit(encrypted.handles[0], encrypted.inputProof);
    await tx.wait();

    const handle = await vault.balanceOf(alice.address);
    const clear = await fhevm.userDecryptEuint(FhevmType.euint64, handle, deployment.address, alice);
    expect(clear).to.be.greaterThanOrEqual(100n);
  });
});
```

## Notes

- Deploy first: `npx hardhat deploy --network sepolia`.
- If `deployments.get(...)` fails, tell the user to deploy first.
- Do not assume the initial state is `0`; Sepolia contracts may already have historical state.
- Configure test timeouts.
- Prefer a single minimal real path: encrypted input, write transaction, read handle, user decrypt.
- Do not use `fhevm.debugger.decrypt*` in Sepolia suites.

## Configuration Check

```bash
npx hardhat --network sepolia fhevm check-fhevm-compatibility --address 0x...
```

If the check fails, first confirm that the contract inherits `ZamaEthereumConfig`, then inspect the `@fhevm/solidity` version and network configuration.
