# DEVNIRA signed native 8-decimal transfer acceptance: REAL evidence still blocked

Builds on the fully verified two-node finality/restart and canonical history work (#37 and #38). This milestone is a safety harness, NOT a wallet or signer, and does not duplicate earlier proof tests. No private keys, mnemonics, seeds, funded mainnet addresses or signing software are included.

To prove genuine DEV spendability later, supply a public, already-signed SCALE extrinsic hex file from an independent DEV-only Dilithium signer and **two simultaneously running local native DEV nodes** with matching nonzero DEV genesis, runtime spec devnira-8dec-native-dev-test-runtime, SS58 prefix 190, symbol DVN, and precision 8. Both tested addresses must be funded DEV-only non-mining accounts; sender and recipient must differ.

The acceptance tool verifies ALL five new critical properties: (1) correct SCALE signed flag and exact tx hash, (2) canonical inclusion in the same finalized block body on both nodes, (3) recipient exact amount in integer 8-decimal base units and sender debit including a positive native fee, (4) nonce increment exactly once and constant native TotalIssuance, and (5) resubmitting identical signed bytes rejected as stale/replay. It also requires identical pre- and post-finalization AccountInfo storage on both peers and refuses foreign/malformed SS58 or wrong runtime chains. It does not accept any JSON report in the repo as evidence by itself.

Example on an explicitly disposable network only, after an independent secure DEV signer actually exists:

    python3 -m scripts.dvn_signed_transfer_acceptance \
      --node-a http://127.0.0.1:19541 --node-b http://127.0.0.1:19542 \
      --trusted-genesis 0x... --from-public DEVNIRA_SS58_190_FROM \
      --to-public DEVNIRA_SS58_190_TO --amount-units 100000000 \
      --signed-extrinsic-file /secure/dev-signed-extrinsic.hex \
      --json-out /secure/dev-finalized-transfer-evidence.json

Source-control GitHub CI intentionally runs **simulation/negative-case tests only**. That workflow being green is not a live signed transaction or a production wallet. Actual signed transaction evidence remains BLOCKED until an independent dev-only signer creates a valid runtime-matched Dilithium extrinsic and the above acceptance runs against two peers. The tool neither generates wallet keys nor authorizes production Send. Approved ZK V2 production verifier/atomic settlement, independent public consensus/genesis, GPU mining, wallets, explorer and audit are separately pending.
