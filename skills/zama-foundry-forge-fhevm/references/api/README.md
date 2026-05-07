# forge-fhevm API 导航

## API 分层

大多数测试只需要第一层：

| 层级 | 读哪个文件 | 什么时候用 |
| --- | --- | --- |
| 常规测试 | `fhevm-test.md` | 写 `FhevmTest`、`encryptUint64`、`decrypt`、`userDecrypt`、`publicDecrypt` |
| 自定义输入证明 | `input-proof-helper.md` | 需要自己组装 input proof，而不是用 `encrypt*` |
| 自定义 KMS 证明 | `kms-decryption-proof-helper.md` | 需要自己控制 `FHE.checkSignatures` 的 cleartext 编码 |
| 自定义 user decrypt 签名 | `user-decrypt-helper.md` | 需要手动核验或生成 user decrypt EIP-712 digest |

## 推荐阅读顺序

1. 普通业务测试：只读 `fhevm-test.md`。
2. public decrypt callback 很复杂：再读 `kms-decryption-proof-helper.md`。
3. encrypted input proof 不是单个 handle：再读 `input-proof-helper.md`。
4. user decrypt 签名需要和前端/SDK 对齐：再读 `user-decrypt-helper.md`。

## 最重要的边界

- `decrypt` 是测试后门，只读本地 plaintext DB，不检查 ACL。
- `publicDecrypt` 会检查 public decrypt flag，并返回 KMS-style proof。
- `userDecrypt` 会检查 user 和 contract 的 persistent ACL，还会验用户签名。
- `buildDecryptionProof` 只造 KMS proof，不检查 ACL，也不证明业务上允许公开。
- `signUserDecrypt` 只造用户签名，不给 handle 授权；授权必须来自合约里的 `FHE.allowThis` 和 `FHE.allow`。

## Source of truth

API 文档可能落后于源码。实际开发和修复测试时按这个顺序确认：

1. 当前项目 remapping 指向的 `forge-fhevm/FhevmTest.sol` 或 helper 源码。
2. 依赖 `forge-fhevm` 的 `docs/api/*.md`。
3. 本目录的整理说明。
