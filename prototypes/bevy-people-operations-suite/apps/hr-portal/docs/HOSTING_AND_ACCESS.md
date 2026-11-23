# Hosting and access

## Company staging review

This company PR uses the existing Django session login for `/people-ops/`, `/hr/`, `/expenses/`, `/insurance/` and `/daily-updates/`, including direct assets. No ChatGPT account is needed on company staging. The account selector changes fictional preview data only; it does not authorize real HR operations. Verify signed-out users are redirected before sharing.

## Original hosted demo approach

The following describes the separate Sites-hosted demo, not the Django staging route.

1. Source remains in the private GitHub repository `shahriyarhassan-HR/bevy-hr-portal-prototype`. GitHub Pages is not enabled.
2. The hosted demo checks company identity on the server on every asset request. It uses Sites' trusted sign-in identity; exact domain `bevycommerce.com` is required.
3. Anyone with a verified company-email ChatGPT account can use the same link. Individual invitations are unnecessary. People using personal ChatGPT accounts must switch accounts. This intentionally includes all company staff, not only PM/dev.
4. Every visitor gets their own browser-local fictional workspace. There is no shared HR database and no shared edits.

The host's outer audience may be public so the login page can be reached; **application content remains server-protected**. Do not mistake a public entry route for public demo assets. Tests must check direct `/seed.mjs`, `/app.js`, `/index.html` and `/styles.css` requests as well as `/`.

## Local computer

Run `python3 serve.py` and open http://127.0.0.1:8080. Bind remains `127.0.0.1`; do not change to all interfaces casually. It is not remotely accessible by default. The local server serves only `web/`, not the repository, tests or documentation. Directory listings should not be relied upon as confidentiality; all local files are dummy assets.

## Private local sharing alternative

If company policy requires hosting on your PC, use a company-approved VPN/private network. With Tailscale configured and team membership approved, `tailscale serve --bg http://127.0.0.1:8080` can publish within that private network. Team network access and ACLs must be configured first; the command alone does not establish a company access policy. Your PC and internet must remain on. Do not use a public tunnel without an independently enforced access layer. Do not open a router port.

## Moving to company-owned SSO hosting

For long-term review, the dev team can deploy the same UI on company-owned staging and place Google Workspace / Microsoft Entra group-based SSO in front of it. Prefer a review group to a whole-company domain if the audience should be limited. Protect the origin, preview URLs, asset paths and alternate domains; verify anonymous and outsider denial. Replace Sites identity headers with validated identity from that hosting provider. Trusting arbitrary inbound email headers would be insecure.

## Free versus paid

This prototype has no paid API or package dependency. Hosting availability and quotas depend on the account/provider; no paid plan, subscription, domain purchase or billing change has been made by this code. Local use has no hosting charge.

## GitHub access

Private source code is separate from demo access. Visiting the demo does not grant repository access. Source collaboration can be managed through an organization team if the repository is later moved into the company organization. A personal private repository may require collaborator permissions for developers; no collaborators have been added automatically.
