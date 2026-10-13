# DEVNIRA independent genesis proposal — NOT LIVE

Independent chain identifier: `devnira-mainnet-v1`. Name: DEVNIRA; symbol DVN. Proposed QPoW/Poseidon2 consensus; 12-second target; 100 million DVN hard cap, 10% (10 million DVN) founders/team/investors allocation and 90% (90 million DVN) GPU/PoW mining allocation; beneficiary addresses and vesting rules pending, initial balances currently empty; 5 DVN initial subsidy; 399/400 multiplier each 50,000 blocks.

`config/genesis-proposal.json` is a **planning document, not a Substrate chain-spec JSON**. It cannot launch a chain.

## Blocking engineering tasks

- Fork and pin actual Quantus upstream source with notices.
- Modify node chain spec, runtime constants, QPoW consensus and reward pallet.
- Produce real WASM runtime and genesis storage state root.
- Set unique network protocol identifiers, bootnodes, address prefix and real genesis hash.
- Build and run independent nodes, mine blocks, and verify network isolation.
- Implement and audit the 10 million DVN genesis allocation with approved beneficiary addresses, vesting/lock rules and transparent accounting; do not insert fabricated addresses.
- Cap miner rewards to the separate 90 million DVN mining allocation and validate total issuance never exceeds 100 million DVN.
- Cross-validate exact integer reward schedule over all epochs.
- Run integration and security tests before a public launch.

No real genesis block hash can be claimed until an actual runtime is built and genesis storage computed.

## Approved team/investor vesting policy

- 3% of total supply (3,000,000 DVN): immediately unlocked at mainnet genesis.
- 7% of total supply (7,000,000 DVN): locked for 730 days from mainnet genesis, then unlocked in one cliff (not gradual linear vesting).
- 90% (90,000,000 DVN): reserved for GPU/PoW mining.
- Implement an on-chain enforceable lock; documentation or a wallet promise alone is insufficient.
- Beneficiary addresses and actual genesis timestamp remain pending; no coins have been distributed.
