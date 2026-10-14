#!/usr/bin/env python3
"""Lock DEVNIRA pre-release nodes to their explicitly compiled LOCAL network.

The pinned Quantus node CLI ships with heisenberg/planck/mainnet chain IDs
AND built-in JSON specs; merely changing the dev chain ID is not sufficient.
Until an independently validated DEVNIRA runtime and genesis exist, reject ALL
foreign live specs and arbitrary --chain paths without trying to load them.
"""
import argparse
from pathlib import Path

MARKER="DEVNIRA PRE-RELEASE: only --chain dev or --chain devnira-local"
REPLACEMENT=r'''	fn load_spec(&self, id: &str) -> Result<Box<dyn sc_service::ChainSpec>, String> {
		// DEVNIRA PRE-RELEASE: only --chain dev or --chain devnira-local
		// is supported. Never import a Quantus Planck, Heisenberg, Mainnet
		// or arbitrary JSON state into the DVN chain database.
		// Independent DVN mainnet MUST use a separately audited genesis and
		// a distinct, future CLI implementation after the full V2 migration.
		match id {
			"dev" | "devnira-local" => Ok(
				Box::new(chain_spec::development_chain_spec()?)
					as Box<dyn sc_service::ChainSpec>
			),
			_ => Err(format!(
				"DEVNIRA pre-release refuses chain '{}' (including Quantus defaults / foreign specs); use --chain dev only. No independent DVN mainnet genesis exists yet",
				id
			)),
		}
	}'''

def patch(root:Path)->None:
    cli=root/"node/src/command.rs"
    src=cli.read_text(encoding="utf-8")
    if MARKER in src:
        raise ValueError("STOP: DEVNIRA chain isolation guard already applied")
    start_marker='\tfn load_spec(&self, id: &str) -> Result<Box<dyn sc_service::ChainSpec>, String> {'
    if src.count(start_marker)!=1:
        raise ValueError("STOP: load_spec signature changed; manually audit node")
    start=src.index(start_marker)
    end=src.find("\n\t}\n}",start)
    if end<0:
        raise ValueError("STOP: CLI load_spec block layout changed")
    prior=src[start:end+3]
    for name in (
        '"mainnet_live_spec"','"mainnet"','"planck_live_spec"','"planck"',
        '"heisenberg_live_spec"','"heisenberg"',
        'ChainSpec::from_json_file','chain_spec::development_chain_spec()',
    ):
        if name not in prior:
            raise ValueError(f"STOP: upstream network selector changed at {name}")
    if 'include_bytes!("chain-specs/' not in prior.replace("\n",""):
        # upstream formats include_bytes!(newline, filename)
        if 'include_bytes!(' not in prior:
            raise ValueError("STOP: foreign baked chain spec embed path changed")
    src=src[:start]+REPLACEMENT+src[end+3:]
    if src.count(MARKER)!=1 or '"mainnet_live_spec"' in src[start:start+len(REPLACEMENT)]:
        raise ValueError("STOP: DEVNIRA source guard invariant")
    cli.write_text(src,encoding="utf-8")
    print("Blocked all inherited Quantus live networks and arbitrary foreign chain specs.")
    print("LOCAL 12-decimal DEVNIRA dev proof candidate only; not independent 8-decimal mainnet.")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("upstream_root",type=Path)
    patch(ap.parse_args().upstream_root)
