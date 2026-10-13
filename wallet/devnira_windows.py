"""DEVNIRA Windows desktop RPC monitor (read-only pre-release wallet shell).

No keys, signing, send/receive or vesting claims. Requires a local DEVNIRA node.
"""
import json
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.request import Request, urlopen
from network_identity import validate_local_rpc, validate_identity

def rpc(endpoint, method, params=None):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
    req = Request(endpoint, body, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=8) as response:
        result = json.load(response)
    if "error" in result:
        raise RuntimeError(str(result["error"]))
    return result.get("result")

class DVNMonitor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DEVNIRA — Node Monitor (Pre-release)")
        self.geometry("690x390")
        self.endpoint = tk.StringVar(value="http://127.0.0.1:9944")
        self.status = tk.StringVar(value="Not connected")
        self.expected_genesis = tk.StringVar(value="")
        self.chain = tk.StringVar(value="—")
        self.genesis = tk.StringVar(value="—")
        self.runtime = tk.StringVar(value="—")
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="DEVNIRA / DVN", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Read-only node monitor. NOT a wallet: no private keys, balances, or transfers.").pack(anchor="w", pady=(4, 20))
        ttk.Label(frame, text="Local RPC endpoint").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.endpoint, width=65).pack(anchor="w", pady=4)
        ttk.Label(frame, text="Trusted DEVNIRA genesis hash (0x + 64 hex digits)").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.expected_genesis, width=65).pack(anchor="w", pady=4)
        ttk.Button(frame, text="Connect / Refresh", command=self.refresh).pack(anchor="w", pady=12)
        for label, value in (("Connection", self.status), ("Chain", self.chain), ("Genesis hash", self.genesis), ("Runtime", self.runtime)):
            ttk.Label(frame, text=label + ":", font=("Segoe UI", 10, "bold")).pack(anchor="w")
            ttk.Label(frame, textvariable=value, wraplength=630).pack(anchor="w", pady=(0, 8))
    def refresh(self):
        url = self.endpoint.get().strip()
        if not url.startswith(("http://127.0.0.1:", "http://localhost:")):
            messagebox.showerror("Local RPC only", "Connect to a local node using 127.0.0.1 or localhost.")
            return
        try:
            validate_local_rpc(url)
            chain = rpc(url, "system_chain")
            genesis = rpc(url, "chain_getBlockHash", [0])
            version = rpc(url, "state_getRuntimeVersion")
            self.chain.set(str(chain))
            self.genesis.set(str(genesis))
            self.runtime.set(str(version.get("specName", "unknown")) + " v" + str(version.get("specVersion", "?")))
            self.status.set("Connected (unverified network)")
        except Exception as exc:
            self.status.set("Disconnected")
            messagebox.showerror("RPC connection failed", str(exc))

if __name__ == "__main__":
    DVNMonitor().mainloop()
