"""Read-only DVN CLI diagnostic cannot present unpinned foreign RPC as DVN."""
import unittest
from spec.ss58_company_account import encode_ss58_account
from wallet.devnira_rpc import diagnostics
from tests.test_wallet_balance import (
    ADDRESS, GENESIS, FINALIZED, ENDPOINT, mock_rpc,
)

class WalletRpcDiagnosticTests(unittest.TestCase):
    def test_trusted_native_node_and_finalized_account(self):
        rpc, calls = mock_rpc()
        report=diagnostics(ENDPOINT,GENESIS,ADDRESS,rpc_fn=rpc)
        self.assertEqual(report["genesis_hash"],GENESIS)
        self.assertEqual(report["account"]["free"],"5.00000001 DVN")
        self.assertEqual(report["account"]["reserved"],"0.00000001 DVN")
        self.assertEqual(report["account"]["finalized_block_hash"],FINALIZED)
        self.assertTrue(calls)

    def test_wrong_chain_never_yields_wallet_balance(self):
        cases=[
            {"chain_getBlockHash":"0x"+"ff"*32},
            {"system_chain":"Quantus"},
            {"state_getRuntimeVersion":{"specName":"quantus-runtime"}},
            {"system_properties":{"tokenSymbol":"DEV","tokenDecimals":12,"ss58Format":189}},
        ]
        for changed in cases:
            rpc, calls=mock_rpc(changed=changed)
            with self.assertRaises(ValueError,msg=str(changed)):
                diagnostics(ENDPOINT,GENESIS,ADDRESS,rpc_fn=rpc)
            self.assertNotIn("state_getStorage",[c[1] for c in calls])

    def test_missing_pinned_genesis_does_not_contact_rpc(self):
        for invalid in ("","untrusted-genesis","0x"+"12"*31):
            rpc,calls=mock_rpc()
            with self.assertRaises(ValueError):
                diagnostics(ENDPOINT,invalid,ADDRESS,rpc_fn=rpc)
            self.assertEqual(calls,[])

if __name__=="__main__":
    unittest.main()
