# DEVNIRA V2 candidate header selection — NO PRODUCTION ACTIVATION

This composes PR #29–31 native custody, exact V2 leaf commitments and 4-ary depth16 roots with an opt-in header-root bridge. The only consensus root slot in pinned qp-header remains unchanged in SCALE layout and digest commitment size.

In actual FRAME native tests, an explicitly opt-in mock runtime publishes its custody V2 root to frame_system's zk tree root during the last zk-tree on_finalize hook, for the deposit block and unchanged following blocks. Inactivated mode preserves original V1 header handling. Mixed V1 and V2 leaves must fail closed.

This DOES NOT establish real independent network finality, authentic historical header preimages, a finalized block hash linked to V2 witness and proof, native/WASM production verifier keys, settlement, signed user extrinsics or actual two-node spendability. Public V2 mode is disabled by default. User-facing Send MUST stay disabled.

Following work requires consensus/fixture migration, historical headers that are actually imported/finalized by independent DVN peers, audited domain-bound V2 VK, atomic custody payouts and a real signed native/WASM two-node network.