# forge-fhevm 测试总览

本目录说明如何把 `zama-fhevm-solidity-core` 里的合约开发模式，落到 Foundry/forge-fhevm 测试里。先读本文件判断测试类型，再打开对应专题。

## 先写哪几类测试

一个 FHEVM 合约最少应覆盖这些路径：

| 测试目标 | 读哪个文件 | 证明什么 |
| --- | --- | --- |
| encrypted input 成功进入合约 | `encrypt.md` | `encrypt*` 生成的 handle/proof 能被 `FHE.fromExternal` 消费 |
| encrypted 计算结果正确 | `decrypt.md` | FHE 运算结果符合预期 |
| 用户真的能解密自己的值 | `decrypt.md` + `acl.md` | `FHE.allowThis` 和 `FHE.allow(user)` 都正确 |
| 未授权用户不能解密 | `acl.md` | ACL 没有过度授权 |
| public decrypt 流程正确 | `decrypt.md` | public flag、KMS proof、`FHE.checkSignatures` 编码一致 |
| ERC7984 token 行为 | `erc7984.md` | mint/burn/transfer/operator/事件金额/disclose 路径正确 |
| 边界值和失败路径 | `fuzz-and-errors.md` | overflow/underflow、错 target、错 signer、错 ACL 都被覆盖 |

如果只写 `decrypt(...)` 断言，测试会很快，但它不能证明 ACL 和真实用户解密流程正确。

## 最短测试骨架

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import {FhevmTest} from "forge-fhevm/FhevmTest.sol";
import {FHE, euint64, externalEuint64} from "@fhevm/solidity/lib/FHE.sol";
import {ZamaEthereumConfig} from "@fhevm/solidity/config/ZamaConfig.sol";

contract ConfidentialVault is ZamaEthereumConfig {
    mapping(address => euint64) private _balances;

    function deposit(externalEuint64 encryptedAmount, bytes calldata proof) external {
        euint64 amount = FHE.fromExternal(encryptedAmount, proof);
        euint64 next = FHE.add(_balances[msg.sender], amount);

        _balances[msg.sender] = next;
        FHE.allowThis(next);
        FHE.allow(next, msg.sender);
    }

    function balanceOf(address account) external view returns (euint64) {
        return _balances[account];
    }
}

contract ConfidentialVaultTest is FhevmTest {
    ConfidentialVault vault;

    function setUp() public override {
        super.setUp();
        vault = new ConfidentialVault();
    }

    function test_deposit() public {
        (externalEuint64 amount, bytes memory proof) = encryptUint64(100, address(vault));
        vault.deposit(amount, proof);
        assertEq(decrypt(vault.balanceOf(address(this))), 100);
    }
}
```

关键点：

- 测试合约继承 `FhevmTest`。
- 覆写 `setUp()` 时先 `super.setUp()`。
- 被测合约继承 `ZamaEthereumConfig`。
- 合约用 `FHE.fromExternal` 接收用户 encrypted input。
- 保存新 handle 后重新设置 ACL。

## 文件导览

- `encrypt.md`：如何用 `encryptBool`、`encryptUintXX`、`encryptAddress` 生成测试输入。
- `decrypt.md`：如何选择 `decrypt`、`publicDecrypt`、`buildDecryptionProof`、`userDecrypt`。
- `acl.md`：如何测试 `allowThis`、`allow`、`allowTransient`、public decrypt flag 和权限传播。
- `erc7984.md`：如何测试 OpenZeppelin ERC7984 confidential token。
- `fuzz-and-errors.md`：如何写 fuzz、边界值、wrapping 和常见错误路径。
- API 签名和 helper 细节：见 `../api/README.md`。

## Source of truth

测试模式来自：

- `src/FhevmTest.sol`
- `docs/guides/encrypt-inputs.md`
- `docs/guides/decrypt-results.md`
- `docs/guides/testing-patterns.md`
- `docs/api/*.md`
- `test/FhevmTest.*.t.sol`
- `test/ERC7984.t.sol`
- `test/helpers/SampleEncryptedToken.sol`

如果 reference 和当前项目依赖不一致，以 remapping 指向的 `forge-fhevm` 源码为准。

## 与 solidity-core patterns 的关系

合约写法仍遵循 `zama-fhevm-solidity-core`：

- 加密输入：`../../../zama-fhevm-solidity-core/references/patterns/encryption.md`
- 解密：`../../../zama-fhevm-solidity-core/references/patterns/decryption.md`
- ACL：`../../../zama-fhevm-solidity-core/references/patterns/acl.md`

本目录只说明这些模式在 Foundry/forge-fhevm 中如何测试。
