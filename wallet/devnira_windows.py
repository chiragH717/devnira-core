"""DEVNIRA Windows wallet — trusted read-only receive and finalized balance preview.

There is NO transaction signing, secret custody or 'Send' button. The native
Dilithium87 challenge signer is tested separately; it is NOT an extrinsic signer.
Do not use this preview with production funds before independent DVN genesis.
"""
import json
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spec.ss58_company_account import verified_company_public_address
from wallet.network_identity import validate_local_rpc, validate_identity
from wallet.devnira_balance import format_dvn, read_finalized_balance

def rpc(endpoint, method, params=None):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    req=Request(endpoint,body,headers={"Content-Type":"application/json"})
    with urlopen(req,timeout=8) as response:
        result=json.load(response)
    if "error" in result:
        raise RuntimeError(str(result["error"]))
    return result.get("result")

class DVNMonitor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DEVNIRA — Wallet Preview (Read-only, NOT signing)")
        self.geometry("765x620")
        self.endpoint=tk.StringVar(value="http://127.0.0.1:9944")
        self.status=tk.StringVar(value="Not connected")
        self.expected_genesis=tk.StringVar(value="")
        self.chain=tk.StringVar(value="—")
        self.genesis=tk.StringVar(value="—")
        self.runtime=tk.StringVar(value="—")
        self.address=tk.StringVar(value="")
        self.receive_address=tk.StringVar(value="—")
        self.free_balance=tk.StringVar(value="—")
        self.reserved_balance=tk.StringVar(value="—")
        self.finalized_at=tk.StringVar(value="—")
        self.connected=False

        frame=ttk.Frame(self,padding=20)
        frame.pack(fill="both",expand=True)
        ttk.Label(frame,text="DEVNIRA / DVN — Read-only Wallet Preview",
                  font=("Segoe UI",17,"bold")).pack(anchor="w")
        ttk.Label(frame,text="No private keys, Send, or transfer signing. Native ZK and independent genesis NOT released.",
                  wraplength=700).pack(anchor="w",pady=(5,12))
        ttk.Label(frame,text="Local RPC endpoint").pack(anchor="w")
        ttk.Entry(frame,textvariable=self.endpoint,width=76).pack(anchor="w",pady=4)
        ttk.Label(frame,text="Trusted independent DEVNIRA genesis hash (must verify outside this app)").pack(anchor="w")
        ttk.Entry(frame,textvariable=self.expected_genesis,width=76).pack(anchor="w",pady=4)
        ttk.Button(frame,text="Verify Network / Refresh",command=self.refresh).pack(anchor="w",pady=(5,12))
        for label,value in (("Connection",self.status),("Chain",self.chain),
                            ("Genesis",self.genesis),("Runtime",self.runtime)):
            ttk.Label(frame,text=label+":",font=("Segoe UI",10,"bold")).pack(anchor="w")
            ttk.Label(frame,textvariable=value,wraplength=700).pack(anchor="w",pady=(0,4))

        ttk.Separator(frame,orient="horizontal").pack(fill="x",pady=10)
        ttk.Label(frame,text="Public DVN SS58-190 address (receive/balance)",
                  font=("Segoe UI",10,"bold")).pack(anchor="w")
        ttk.Entry(frame,textvariable=self.address,width=76).pack(anchor="w",pady=4)
        actions=ttk.Frame(frame)
        actions.pack(anchor="w",pady=5)
        ttk.Button(actions,text="Validate Receive Address",command=self.validate_receive).pack(side="left",padx=(0,6))
        ttk.Button(actions,text="Copy Receive Address",command=self.copy_receive).pack(side="left",padx=(0,6))
        ttk.Button(actions,text="Read Finalized Balance",command=self.show_balance).pack(side="left")
        for label,value in (("Verified Public Address",self.receive_address),
                            ("Free Balance",self.free_balance),
                            ("Reserved Balance",self.reserved_balance),
                            ("Finalized Block",self.finalized_at)):
            ttk.Label(frame,text=label+":",font=("Segoe UI",10,"bold")).pack(anchor="w")
            ttk.Label(frame,textvariable=value,wraplength=700).pack(anchor="w",pady=(0,4))

    def _reset_connection(self):
        self.connected=False
        self.chain.set("—")
        self.genesis.set("—")
        self.runtime.set("—")
        self.receive_address.set("—")
        self.free_balance.set("—")
        self.reserved_balance.set("—")
        self.finalized_at.set("—")
        self.status.set("Disconnected")

    def refresh(self):
        self._reset_connection()
        endpoint=self.endpoint.get().strip()
        try:
            validate_local_rpc(endpoint)
            chain=rpc(endpoint,"system_chain")
            genesis=rpc(endpoint,"chain_getBlockHash",[0])
            version=rpc(endpoint,"state_getRuntimeVersion")
            validate_identity(chain,version,genesis,self.expected_genesis.get().strip())
            if version.get("specName")!="devnira-runtime":
                raise ValueError("Unexpected DEVNIRA runtime identity")
            props=rpc(endpoint,"system_properties")
            if not isinstance(props,dict) or (
                props.get("tokenSymbol"),props.get("tokenDecimals"),props.get("ss58Format")
            )!=("DVN",8,190):
                raise ValueError("Incorrect 8-decimal DVN / SS58 190 network properties")
            self.chain.set(chain)
            self.genesis.set(genesis)
            self.runtime.set(str(version["specName"])+" v"+str(version.get("specVersion","?")))
            self.connected=True
            self.status.set("Matched user-supplied genesis pin (local RPC is not authenticated)")
        except Exception as exc:
            self._reset_connection()
            messagebox.showerror("Network verification failed",str(exc))

    def _verified_receive(self):
        if not self.connected:
            raise ValueError("Verify the independent DEVNIRA chain and trusted genesis first")
        return verified_company_public_address(self.address.get().strip())

    def validate_receive(self):
        try:
            address=self._verified_receive()
            self.receive_address.set(address)
            self.free_balance.set("—")
            self.reserved_balance.set("—")
            self.finalized_at.set("—")
        except Exception as exc:
            self.receive_address.set("—")
            messagebox.showerror("Invalid receive address",str(exc))

    def copy_receive(self):
        try:
            address=self._verified_receive()
            if self.receive_address.get()!=address:
                raise ValueError("Validate this exact public receiving address first")
            self.clipboard_clear()
            self.clipboard_append(address)
        except Exception as exc:
            messagebox.showerror("Address not verified",str(exc))

    def show_balance(self):
        self.free_balance.set("—")
        self.reserved_balance.set("—")
        self.finalized_at.set("—")
        try:
            address=self._verified_receive()
            result=read_finalized_balance(
                self.endpoint.get().strip(),self.expected_genesis.get().strip(),address
            )
            self.receive_address.set(result.address)
            self.free_balance.set(format_dvn(result.free_units))
            self.reserved_balance.set(format_dvn(result.reserved_units))
            self.finalized_at.set(result.at_finalized_hash)
        except Exception as exc:
            messagebox.showerror("Finalized balance unavailable",str(exc))

if __name__=="__main__":
    DVNMonitor().mainloop()
