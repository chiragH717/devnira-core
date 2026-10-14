"""DVN receive/balance reader: exact SCALE, finalized state and fail-closed identity."""
import unittest
from hashlib import blake2b

from spec.ss58_company_account import encode_ss58_account
from wallet.devnira_balance import (
    AccountBalance, MAX_SUPPLY_UNITS, UNIT, format_dvn,
    parse_system_account, read_finalized_balance, storage_key_for_account,
)

ADDRESS=encode_ss58_account(bytes(range(1,33)))
GENESIS="0x"+"af"*32
FINALIZED="0x"+"ba"*32
ENDPOINT="http://127.0.0.1:9944"

def sample_account(nonce=3,free=500_000_001,reserved=1,frozen=100_000_000):
    # Matching FRAME AccountInfo<u32, pallet_balances::AccountData<u128>>
    return "0x"+b"".join([
        nonce.to_bytes(4,"little"), (1).to_bytes(4,"little"),
        (1).to_bytes(4,"little"), (0).to_bytes(4,"little"),
        free.to_bytes(16,"little"), reserved.to_bytes(16,"little"),
        frozen.to_bytes(16,"little"), (0).to_bytes(16,"little"),
    ]).hex()

def mock_rpc(*, changed=None, missing_account=False):
    responses={
        "system_chain":"DEVNIRA Independent Testnet",
        "state_getRuntimeVersion":{"specName":"devnira-runtime","specVersion":1},
        "chain_getBlockHash":GENESIS,
        "system_properties":{"tokenSymbol":"DVN","tokenDecimals":8,"ss58Format":190},
        "chain_getFinalizedHead":FINALIZED,
        "state_getStorage":None if missing_account else sample_account(),
    }
    if changed:
        responses.update(changed)
    calls=[]
    def call(url,method,params=None):
        calls.append((url,method,params))
        return responses[method]
    return call,calls

class DvnBalanceTests(unittest.TestCase):
    def test_known_system_account_storage_key(self):
        raw=bytes(range(1,33))
        key=storage_key_for_account(ADDRESS)
        expected=("0x26aa394eea5630e07c48ae0c9558cef7"
                  "b99d880ec681799c0cf30e8886371da9")
        self.assertTrue(key.startswith(expected))
        self.assertEqual(
            key, expected + (blake2b(raw,digest_size=16).digest()+raw).hex()
        )
        self.assertEqual(len(bytes.fromhex(key[2:])),80)

    def test_native_balances_are_never_rounded(self):
        self.assertEqual(format_dvn(1),"0.00000001 DVN")
        self.assertEqual(format_dvn(500_000_001),"5.00000001 DVN")
        self.assertEqual(format_dvn(MAX_SUPPLY_UNITS),"100,000,000.00000000 DVN")
        self.assertEqual(parse_system_account(sample_account()),
                         (3,500_000_001,1,100_000_000))
        for amount in (-1,MAX_SUPPLY_UNITS+1,1.5,True):
            with self.assertRaises(ValueError):
                format_dvn(amount)

    def test_queries_only_finalized_state_after_trusted_genesis(self):
        rpc,calls=mock_rpc()
        result=read_finalized_balance(ENDPOINT,GENESIS,ADDRESS,rpc_fn=rpc)
        self.assertIsInstance(result,AccountBalance)
        self.assertEqual(result.at_finalized_hash,FINALIZED)
        self.assertEqual(result.free_units,500_000_001)
        self.assertEqual(result.reserved_units,1)
        self.assertEqual(result.total_units,500_000_002)
        self.assertEqual(calls[-1],(
            ENDPOINT,"state_getStorage",[storage_key_for_account(ADDRESS),FINALIZED]))
        self.assertEqual([x[1] for x in calls],[
            "system_chain","state_getRuntimeVersion","chain_getBlockHash",
            "system_properties","chain_getFinalizedHead","state_getStorage"
        ])

    def test_nonexistent_account_reports_zero_not_fake_funding(self):
        rpc,_=mock_rpc(missing_account=True)
        result=read_finalized_balance(ENDPOINT,GENESIS,ADDRESS,rpc_fn=rpc)
        self.assertEqual((result.nonce,result.total_units,result.frozen_units),(0,0,0))

    def test_stop_before_chain_state_on_invalid_network_or_address(self):
        for endpoint,genesis,address in [
            ("https://example.org:9944",GENESIS,ADDRESS),
            (ENDPOINT,"",ADDRESS),
            (ENDPOINT,"0x00",ADDRESS),
            (ENDPOINT,GENESIS,encode_ss58_account(bytes(range(1,33)),189)),
            (ENDPOINT,GENESIS,ADDRESS[:-1]+"!"),
        ]:
            rpc,calls=mock_rpc()
            with self.assertRaises(ValueError):
                read_finalized_balance(endpoint,genesis,address,rpc_fn=rpc)
            self.assertEqual(calls,[])

    def test_rejects_untrusted_chain_and_metadata_before_reading_balance(self):
        cases=[
            {"system_chain":"Quantus"},
            {"state_getRuntimeVersion":{"specName":"quantus-runtime"}},
            {"chain_getBlockHash":"0x"+"cd"*32},
            {"system_properties":{"tokenSymbol":"QTC","tokenDecimals":12,"ss58Format":189}},
            {"system_properties":{"tokenSymbol":"DVN","tokenDecimals":12,"ss58Format":190}},
            {"chain_getFinalizedHead":"not-a-hash"},
        ]
        for changed in cases:
            rpc,calls=mock_rpc(changed=changed)
            with self.assertRaises(ValueError, msg=str(changed)):
                read_finalized_balance(ENDPOINT,GENESIS,ADDRESS,rpc_fn=rpc)
            self.assertNotIn("state_getStorage",[x[1] for x in calls])

    def test_rejects_unknown_scale_layout_and_oversupply(self):
        for bad in ("0x", "0xzz", "0x00", "0x" + "00"*81,
                    sample_account(free=MAX_SUPPLY_UNITS+1),
                    sample_account(free=MAX_SUPPLY_UNITS,reserved=1)):
            with self.assertRaises(ValueError):
                parse_system_account(bad)

if __name__=="__main__":
    unittest.main()
