# DEVNIRA Core — initial development bootstrap

**Status:** Specification and Python reference tests only. This repository does not yet contain an operational DEVNIRA node, miner, wallet, testnet or mainnet.

## Approved project parameters

- Coin: DEVNIRA (DVN)
- Independent Layer-1 proof-of-work network; Quantus QPoW / Poseidon2 is the selected technical reference, pending source/license and integration verification.
- Target block time: 12 seconds.
- Maximum issuance: 100,000,000 DVN; 10% (10,000,000 DVN) allocated to investors/founders/team and 90% (90,000,000 DVN) reserved for GPU/PoW mining. Allocation recipients, vesting and exact genesis implementation are not yet finalized.
- Initial subsidy: 5 DVN per block.
- Every 50,000 blocks: reward multiplied by 399/400, with exact integer-floor computation based on the initial reward.
- Minimum subsidy: 1 base unit (0.00000001 DVN) until the 90,000,000 DVN mining allocation is exhausted, then zero.
- Mining goals: NVIDIA and AMD GPUs, official miner plus verified third-party compatibility.
- Wallet goals: Windows and Android.

## Local reference tests

Run `python -m unittest discover -s tests -v`.

## Next implementation milestones

1. Review and pin the upstream Quantus source, its license and dependencies.
2. Implement independent chain specification, genesis, network identity and address format.
3. Port the emission schedule to the actual runtime with deterministic bounded-integer arithmetic and test vectors.
4. Verify QPoW miner protocol and hardware compatibility on an isolated local network.
5. Test chain sync, consensus, reorgs, difficulty adjustment and supply accounting before public launch.

**Important:** These Python routines are reference examples, not production consensus code. Full supply exhaustion height and reward rounding must be validated in the target runtime before deployment.
