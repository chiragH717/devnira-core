"use strict";
const statusElement = document.getElementById("node-status");
const output = document.getElementById("block-output");
const form = document.getElementById("block-form");
async function jsonReply(path) {
  const response = await fetch(path, {cache: "no-store", headers: {"Accept":"application/json"}});
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) throw new Error("Explorer API is not configured");
  if (!response.ok) throw new Error(response.status === 404 ? "Block not found" : "Verified chain unavailable");
  return response.json();
}
(async () => {
  try {
    const data = await jsonReply("/api/status");
    if (data.token_symbol !== "DVN" || data.token_decimals !== 8 ||
        data.ss58_format !== 190 || data.mainnet_ready !== false) throw new Error("Unexpected network data");
    statusElement.textContent = "Verified development RPC; finalized #" + data.finalized_height;
  } catch (_) {
    statusElement.textContent = "Offline — no verified independent DEVNIRA RPC connected";
  }
})();
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = document.getElementById("height").value;
  if (!/^(0|[1-9][0-9]{0,19})$/.test(value) || BigInt(value) > 18446744073709551615n) {
    output.textContent = "Enter a valid uint64 block height";
    return;
  }
  output.textContent = "Checking pinned development RPC…";
  try {
    const block = await jsonReply("/api/block/" + value);
    output.textContent = JSON.stringify(block, null, 2);
  } catch (error) {
    output.textContent = error.message;
  }
});
