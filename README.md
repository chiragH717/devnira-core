# DEVNIRA (DVN) independent GPU-mined Layer-1

**Engineering status: PRE-RELEASE DEVELOPMENT — NOT MAINNET READY.**

- [Complete project roadmap, status chart and launch blockers](docs/MASTER_ROADMAP.md): Blockchain, Active ZK V2, independent runtime/genesis, company signing wallet, NVIDIA/AMD two-node mining, mining pool, block explorer, website `devnira.co`, Android wallet, RPC, security and release.
- [Combined public-product development candidates](docs/PUBLIC_PRODUCT_CANDIDATES.md): static site, local genesis-guarded read-only block API and offline pool accounting preview (none deployed or proof of DVN mining).
- [Detailed Stage 2 engineering status](docs/FOUR_POINT_STATUS.md)
- [Independent mainnet genesis policy](docs/GENESIS_STATUS.md)
- [Current source-test and release evidence rules](docs/LAUNCH_READINESS.md)
- [Public GitHub Actions development test runs](https://github.com/chiragH717/devnira-core/actions)

Consensus target: 12-second QPoW/Poseidon2; DEVNIRA prefix SS58-190; eight decimal places; fixed 100M DVN lifetime supply (90M miner-only budget, 10M one company-controlled treasury: 3M liquid at genesis and 7M locked for twelve monthly calendar cliffs).

The isolated DEVNIRA **12-decimal development-node candidate** [compiled and rejected inherited Quantus live chains](https://github.com/chiragH717/devnira-core/actions/runs/38545679156). An independent 8-decimal DEVNIRA runtime/genesis, V2 on-chain proof migration, mainnet signing wallet, and hardware GPU mining are **not** completed.

No unverified chain IDs, new production keys or wallet seeds should be committed. Never confuse a green development workflow or a read-only wallet preview with a launch-ready network.
