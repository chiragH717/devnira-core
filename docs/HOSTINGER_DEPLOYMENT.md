# DEVNIRA static website on Hostinger (domain already purchased)

**Owner says the public domain `devnira.co` was bought from Hostinger.**
Domain registration alone does not guarantee a Web Hosting plan: confirm in
Hostinger hPanel that `devnira.co` has a hosting website attached.

## 1. Build a safe package

GitHub Actions workflow:
`DEVNIRA Hostinger static website ZIP (NOT MAINNET)`.
Download the workflow artifact named
`DEVNIRA-HOSTINGER-STATIC-WEBSITE-NOT-MAINNET`, then extract the outer
GitHub artifact ZIP to obtain `devnira-hostinger-static-NOT-MAINNET.zip`
and SHA256 checksum. Alternatively run
`python3 scripts/package_hostinger_website.py` locally from the repo.
Keep the original inner website zip; its root contains:
`index.html`, `styles.css`, and `app.js`.

## 2. Upload to Hostinger

1. Sign in to **Hostinger hPanel**; check Websites → `devnira.co` →
   Dashboard. If needed attach the owned domain to a **Web Hosting** plan,
   then connect DNS using Hostinger's instructions.
2. Go to **File Manager** → website's **public_html**.
   Back up an existing public site before replacing anything.
3. Upload the **inner website ZIP** to `public_html`, then extract it
   there. **Confirm `public_html/index.html` exists**; never leave
   an extra `website/` folder between it and `public_html`.
4. Enable the SSL certificate and HTTPS for the domain inside Hostinger.
   Confirm HTTPS loads the page/assets, and mobile navigation works.
5. This static site has **no** public DVN RPC/backend. Block lookup will
   legitimately say offline. Do not expose an unverified or unsecured
   blockchain RPC through hosting.

## Not completed by creating this package

This workflow **does not sign into Hostinger, set DNS records, upload files,
activate SSL or prove the domain is live**. It packages source only.
The content explicitly says DEVNIRA is NOT MAINNET. Never publish fake miner
rewards, wallet download buttons or balances.
