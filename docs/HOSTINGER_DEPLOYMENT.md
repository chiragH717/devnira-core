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

## Reusing a domain previously pointed to another website

- Your registered `devnira.co` stays yours; domain registration is different from buying hosting.
- **Before changing DNS**, export the current DNS zone records and preserve the existing website, email MX/TXT/SPF/DKIM/DMARC records and any other subdomains. Find out where `@` and `www` currently point.
- Create the new Hostinger hosting website (Custom PHP/HTML), upload the static site ZIP, and preview it using Hostinger's temporary URL.
- If Hostinger reports **domain already used**, remove the old Hostinger website/domain association by changing the old site's domain to a temporary one or request Hostinger support assistance. Changing nameservers does not detach a domain attached to a different Hostinger account.
- Only after the new site is verified and you authorize replacing the previous website should you change the root-domain/www A/CNAME targets. Avoid wholesale nameserver swaps if an existing DNS zone supports email or other services. Preserve TTL/records and confirm HTTPS.
- Never provide passwords, 2FA codes, recovery codes or private wallet keys in GitHub or chat. Grant access through a proper account-sharing/invitation flow supported by the provider, or run a browser session in ChatGPT Work with your own sign-in.

**No Hostinger deployment or DNS change has been made by these commits.** The existing site remains unaffected by the repository changes.
