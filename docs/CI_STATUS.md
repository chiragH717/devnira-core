# DEVNIRA CI setup

Two workflows are present:
- `verify.yml`: reference Python tests, standalone Rust crate tests, JSON genesis-proposal assertions.
- `upstream-build.yml`: **manual trigger only**, clones and tries building original Quantus source. This does NOT compile a DEVNIRA node or create a DEVNIRA genesis.

CI results must be read from the GitHub Actions tab. Workflow files being committed does not prove they passed.

Known limitations:
- Rust reference intentionally panics for epoch >= 2; it is NOT deployable.
- The proposed chain spec is not wired into upstream.
- Quantus source is not vendored into this repository.
- No real DEVNIRA genesis, binary, testnet or GPU miner has been built or tested.

Acceptance criteria remain open until verified.
