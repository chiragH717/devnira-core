# DEVNIRA combined public-product development candidate

**Not launched; not evidence of a mainnet.** This source addition builds useful development-only pieces without pretending the missing network, signing wallet, pool verifier, GPU hardware or external website deployment exists.

## Delivered in this batch

- `website/`: responsive static devnira.co **source candidate**, with supply policy, GPU/wallet disclosures, roadmap, developer links and a no-fake-data block lookup UI. Hostname/DNS/TLS, legal pages, localization and downloads **not deployed**.
- `services/network_rpc.py`: loopback-only, read-only JSON-RPC client that refuses an unset genesis, wrong 8-decimal/DVN/SS58 properties, Quantus or ambiguous chain names, too-large/malformed responses, or RPC methods with write effects. No secrets stored.
- `services/explorer_api.py`: development endpoints `/api/status`, `/api/block/<uint64>`, `/api/hash/<0x32byte>`. Returns raw SCALE extrinsics, no account/history index, no proven mainnet finality. Runs on loopback only by default.
- `pool/share_ledger.py`: deterministic integer-only, duplicate-resistant proportional **payout preview** from externally-authorized share records. It does NOT verify PoW, offer miner connections, calculate actual chain rewards, send transfers, hold wallets or authenticate external validator attestations. Never expose it as a real mining pool.

## Run the local explorer, only after a genuine independent chain exists

```sh
export DVN_RPC_URL=http://127.0.0.1:9944
export DVN_GENESIS_HASH=0x... # actual independent 32-byte genesis, NEVER a made-up value
python3 -m services.explorer_api
curl http://127.0.0.1:8777/api/status
curl http://127.0.0.1:8777/api/block/0
```

Serve `website/` separately using a simple static host during development. For the Explorer panel to work, an operator must explicitly configure reverse-proxy paths to the local read-only API. No public exposure is approved until real chain identity, TLS, rate limits, indexer authorization, and security audit exist.

## Mandatory missing production pieces

1. Active V2 leaf, private+public recursive aggregator, prover/verifier keys, membership/nullifiers/anti-replay and on-chain withdrawal settlement.
2. Compatible independent 8-decimal DVN native + WASM chain, secure independent genesis, real treasury public address and 12-cliff vesting.
3. Signed Windows wallet and secured Android signer/recovery, both tested against real genesis.
4. Two independently synchronized nodes with real NVIDIA/AMD validated PoW rewards; then consensus-authorized pool jobs/shares, accounting proofs and wallet-based on-chain payouts.
5. Explorer canonical indexer, reorg handling, decoded SCALE events/transactions, account/address search, real supply and reward feeds, public infrastructure.
6. Website DNS/TLS/deployment, genuine verified binary downloads, terms/privacy, monitoring, independent audit and release evidence.

Source compilation/unit tests of these candidates do **not** change `scripts/release_evidence_gate.py`, turn mainnet on or satisfy the hardware/keys human gates.
