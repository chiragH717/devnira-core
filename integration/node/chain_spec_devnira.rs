// DEVNIRA fork adaptation of Quantus node/src/chain_spec.rs
// Source: Quantus-Network/chain, MIT-style LICENSE; retain original notices on fork.
// IMPORTANT: This function alone does NOT create a separate genesis: the
// runtime preset MUST be replaced with a zero-premine DEVNIRA preset.
use quantus_runtime::WASM_BINARY;
use sc_service::{ChainType, Properties};
use serde_json::json;

pub type ChainSpec = sc_service::GenericChainSpec;

pub fn devnira_development_chain_spec() -> Result<ChainSpec, String> {
	let mut properties = Properties::new();
	properties.insert("tokenDecimals".into(), json!(8));
	properties.insert("tokenSymbol".into(), json!("DVN"));
	properties.insert("ss58Format".into(), json!(190));

	Ok(ChainSpec::builder(
		WASM_BINARY.ok_or_else(|| "DEVNIRA runtime wasm not available".to_string())?,
		None,
	)
	.with_name("DEVNIRA Local Development")
	.with_id("devnira-local")
	.with_protocol_id("devnira-local-v1")
	.with_chain_type(ChainType::Development)
	.with_genesis_config_preset_name(sp_genesis_builder::DEV_RUNTIME_PRESET)
	.with_properties(properties)
	.build())
}
