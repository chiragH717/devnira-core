"""DEVNIRA Windows wallet — trusted read-only receive and finalized balance preview.

There is NO transaction signing, secret custody or 'Send' button. The native
Dilithium87 challenge signer is tested separately; it is NOT an extrinsic signer.
Do not use this preview with production funds before independent DVN genesis.
"""
import json
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spec.ss58_company_account import verified_company_public_address
from wallet.network_identity import validate_local_rpc, validate_identity
from wallet.devnira_balance import format_dvn, read_finalized_balance, rpc
from wallet.company_wallet_prepare import (
    create_offline_keygen_command, create_public_ownership_challenge,
    verify_offline_company_certificate, verified_native_wallet_binary,
)

class DVNMonitor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DEVNIRA — Receive + Offline Company Wallet Setup (NO SEND)")
        self.geometry("820x690")
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

        self.native_cli=tk.StringVar(value="")
        self.native_sha256=tk.StringVar(value="")
        self.company_wallet_address=tk.StringVar(value="")
        self.public_company_key=tk.StringVar(value="")
        self.ownership_status=tk.StringVar(value="No ownership certificate verified")
        self.challenge=None

        tabs=ttk.Notebook(self)
        tabs.pack(fill="both",expand=True)
        frame=ttk.Frame(tabs,padding=20)
        tabs.add(frame,text="Public Receive / Balance")
        setup=ttk.Frame(tabs,padding=20)
        tabs.add(setup,text="Offline Company Wallet")
        self._build_offline_company_wallet(setup)
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


    def _build_offline_company_wallet(self, frame):
        """Owner controls native terminal. Python never reads the mnemonic."""
        ttk.Label(frame,text="Company Treasury — Offline Public Wallet Setup",
                  font=("Segoe UI",17,"bold")).pack(anchor="w")
        ttk.Label(frame,text=(
            "This tab works BEFORE mainnet. No blockchain, balance, Send or "
            "transaction signing is enabled. Your recovery words NEVER enter this app."
        ),wraplength=745).pack(anchor="w",pady=(4,12))
        ttk.Label(frame,text="1. Choose your AUDITED locally compiled DEVNIRA native CLI (.exe)").pack(anchor="w")
        native=ttk.Frame(frame)
        native.pack(fill="x",pady=4)
        ttk.Entry(native,textvariable=self.native_cli,width=84).pack(side="left",fill="x",expand=True)
        ttk.Button(native,text="Browse",command=self._select_native_cli).pack(side="left",padx=6)
        ttk.Label(frame,text="2. Paste its independently obtained SHA256 (64 lowercase hex characters)").pack(anchor="w")
        ttk.Entry(frame,textvariable=self.native_sha256,width=85).pack(anchor="w",pady=4)
        ttk.Button(frame,text="Verify native CLI + copy OFFLINE generation command",
                   command=self._copy_keygen).pack(anchor="w",pady=(5,9))
        ttk.Label(frame,text=(
            "Open your own local PowerShell terminal and paste the command. "
            "Back up the mnemonic ON PAPER / encrypted offline storage. "
            "Never paste recovery words into ChatGPT, GitHub or website forms."
        ),wraplength=745).pack(anchor="w")
        ttk.Separator(frame,orient="horizontal").pack(fill="x",pady=10)
        ttk.Label(frame,text="3. Paste ONLY the newly generated PUBLIC DVN SS58-190 address").pack(anchor="w")
        ttk.Entry(frame,textvariable=self.company_wallet_address,width=85).pack(anchor="w",pady=4)
        ttk.Button(frame,text="Copy PUBLIC address",command=self._copy_public_company_address).pack(anchor="w")
        ttk.Button(frame,text="Create and save 24-hour PUBLIC ownership challenge",
                   command=self._save_ownership_challenge).pack(anchor="w",pady=(8,4))
        ttk.Label(frame,text=(
            "Sign the challenge's exact message on your secure native CLI with "
            "key devnira-sign. Do not use public CI test phrases. "
            "The signed certificate contains ONLY public key, signature and challenge."
        ),wraplength=745).pack(anchor="w",pady=(3,9))
        ttk.Button(frame,text="Load signed PUBLIC certificate and verify Dilithium87",
                   command=self._verify_company_certificate).pack(anchor="w")
        ttk.Label(frame,textvariable=self.ownership_status,wraplength=745,
                  font=("Segoe UI",10,"bold")).pack(anchor="w",pady=(8,3))
        ttk.Label(frame,text=(
            "Not a production wallet or spendable 10M DVN. The 3M+7M company "
            "genesis allocation is OFF-CHAIN until V2 runtime/genesis audits pass."
        ),wraplength=745).pack(anchor="w",pady=(8,0))

    def _select_native_cli(self):
        chosen=filedialog.askopenfilename(title="Select independently trusted DEVNIRA native CLI",
            filetypes=[("Windows program","*.exe")])
        if chosen:
            self.native_cli.set(chosen)
            self.ownership_status.set("CLI changed — reverify signer and public ownership")

    def _copy_keygen(self):
        try:
            command=create_offline_keygen_command(
                self.native_cli.get(),self.native_sha256.get())
            self.clipboard_clear()
            self.clipboard_append(command)
            messagebox.showinfo("OFFLINE command copied",
                "Open PowerShell on YOUR secure Windows computer and paste "
                "the copied hash-checked command. Record seed/recovery words "
                "OFFLINE and NEVER share them. This app does not see the seed.")
        except Exception as exc:
            messagebox.showerror("Native company wallet not ready",str(exc))

    def _copy_public_company_address(self):
        try:
            address=verified_company_public_address(self.company_wallet_address.get().strip())
            self.clipboard_clear()
            self.clipboard_append(address)
        except Exception as exc:
            messagebox.showerror("Invalid public DVN address",str(exc))

    def _save_ownership_challenge(self):
        try:
            challenge=create_public_ownership_challenge(
                self.company_wallet_address.get().strip())
            destination=filedialog.asksaveasfilename(title="Save PUBLIC ownership challenge",
                defaultextension=".json",filetypes=[("JSON","*.json")])
            if not destination:
                return
            # Exclusive create: never replace an existing approval/certificate.
            with Path(destination).open("x",encoding="utf-8") as stream:
                json.dump(challenge,stream,indent=2,sort_keys=True)
                stream.write("\n")
            self.challenge=challenge
            self.ownership_status.set("Public 24-hour challenge saved; native signature required")
        except Exception as exc:
            messagebox.showerror("Challenge not saved",str(exc))

    def _verify_company_certificate(self):
        self.ownership_status.set("Public ownership has NOT been verified")
        try:
            filename=filedialog.askopenfilename(title="Select signed PUBLIC certificate",
                filetypes=[("JSON","*.json")])
            if not filename:
                return
            file=Path(filename)
            if file.stat().st_size>100_000:
                raise ValueError("Public certificate unexpectedly large")
            certificate=json.loads(file.read_text(encoding="utf-8"))
            expected=self.company_wallet_address.get().strip()
            verified_company_public_address(expected)
            if certificate.get("company_address")!=expected:
                raise ValueError("Certificate address does not match current company address")
            outcome=verify_offline_company_certificate(
                certificate,self.native_cli.get(),self.native_sha256.get())
            if outcome["company_address"]!=expected:
                raise ValueError("Native signer returned a different owner")
            self.ownership_status.set("VERIFIED: genuine signed PUBLIC DVN account "+expected)
        except Exception as exc:
            messagebox.showerror("Company ownership not verified",str(exc))

if __name__=="__main__":
    DVNMonitor().mainloop()
