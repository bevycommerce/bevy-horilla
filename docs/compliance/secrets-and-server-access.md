# Secrets and server access

AWS and WhatsApp credentials have reached this repository's git history before — the `secret-scan`
job in `.github/workflows/quality.yml` exists as a re-occurrence guard, not a hypothetical. History
is immutable: a secret committed here cannot be removed by the person who committed it.

Separately: this is an HR system. A database dump is every employee's salary, address and contract.
It never belongs in a diff, a scratch file inside the repository, or a chat message.

## Do

- Keep real configuration in the server's `.env`, which stays on the server. `.env.dist` is the
  public template — add every new variable there with a safe placeholder and a comment.
- Put the staging database password in the server `.env` as `POSTGRES_PASSWORD`.
- Ask the person to run anything that needs a server, and report what you need run.
- Write temporary files to the session scratchpad, never into the working tree.
- If you believe a secret is already committed, say so and stop. Rotation comes before cleanup.

## Do not

- Commit `.env`, `*.sql`, `*.dump`, `*.zip`, `media/`, a SQLite file, a TLS key, an API key, a
  service-account JSON, or a password — including in a test fixture or a docstring.
- SSH to any server, or run a command through a tunnel to one.
- Run `make restore`, `make wipe`, `make backup`, or any script that copies production data.
- Point a local or staging configuration at the production database, or publish Postgres or Redis on
  a public interface. [`v1-to-v2.md`](../v1-to-v2.md) spells out the cutover constraints.
- Paste a credential into a PR description, an issue, a commit message or a comment, even redacted.
- Disable or narrow the `gitleaks` scan, `.gitleaks.toml`, or the `pip-audit` gate.
- Print a secret into a build log. The scan runs with `--redact` for this reason; keep it that way.
