# DEVNIRA Windows Company Wallet — downloadable combined PREVIEW

This build assembles the independently CI-tested DEVNIRA native Windows
Dilithium87 CLI and the Windows GUI into **one verified ZIP**, which is
much easier to use before the company shares its public address.

- Native CLI is from immutable
  [successful run 38599371352](https://github.com/chiragH717/devnira-core/actions/runs/38599371352),
  pinned to commit d307f43daccd81a33e7db5a8ef589cb04d2af6f2.
- GUI is from immutable
  [successful run 38588478821](https://github.com/chiragH717/devnira-core/actions/runs/38588478821),
  pinned to commit 8a411f107a59fb707b793e9fbb412f1a4545b1eb.
- For each run GitHub must report `conclusion: success`, the exact
  commit and exact artifact name. SHA256 of each EXE MUST match its own
  archived Windows build checksum. If anything disagrees the packaging
  fails. This alone does NOT establish independent source/security audit.
- GitHub bundle workflow publishes artifact
  `DEVNIRA-COMPANY-WINDOWS-OFFLINE-PREVIEW-NOT-MAINNET`. Extract the
  outer GitHub artifact ZIP, then the enclosed website-style bundle ZIP,
  and inspect `READ-ME-FIRST.txt` and `manifest.json`.

**Company owner instructions:** Use the Windows GUI on a trusted Windows PC,
choose the included native executable in the Offline Company Wallet tab,
and enter its digest independently obtained from the audited build.
The GUI will copy a PowerShell command; run the command only in your own
interactive terminal. Record the resulting secret mnemonic OFFLINE.
The public DVN SS58-190 address is the only value needed to identify
the proposed company allocation. Signed ownership verification is
required before genesis. **Never share recovery words, private keys
or vault passwords.**

## Important restrictions

The binaries are development-only and unsigned. The embedded Rust
runtime remains a foreign-derived 12-decimal development source, not the
independent 8-decimal DEVNIRA chain. The GUI is for public-address
preparation and read-only local RPC on an independently pinned future
chain. It has **no Send, no secure audited production custody, no running
DVN mainnet, no transferable DVN balances and no actual 10M treasury**.
Do not solicit deposits or distribute this as a production wallet.
