# Internal HR (bevy-horilla)

This is the internal HR app. Work lands on `staging`, which deploys to https://hr-portal.bevy.dev. `horilla-external` is a different product. Leave it alone.

## How to change code

- Create the branch from `staging`, and open the pull request against `staging`.
- Change only what the task needs. Leave unrelated files, formatting, and refactors out of the diff.
- Keep one change per pull request. In the description, say what changed, why, and how to click-test it.
- Before committing, read the full diff. Remove debug code, leftover files, and anything that does not belong. Match the surrounding code.
- Do not add screenshots, images, or extra markdown notes.

## Schema

A new table or column belongs in a committed Django migration in the same pull request. Say that in the description. The staging boot runs `migrate`. Do not run `makemigrations` or `migrate` on the server.

## Do not change

Leave these alone unless the task names that file:

- `docker-compose.yaml`, `Dockerfile`, `entrypoint.sh`, `Makefile`, `scripts/`
- `horilla/settings.py` and `horilla/auth_migrations/`
- Payroll calculation, login, and permission checks
- `.github/`

Do not commit `.env`, `*.sql`, `*.zip`, or `media/`. The database password belongs in the server `.env` as `POSTGRES_PASSWORD`. Do not put passwords, keys, or dump files in the diff. Do not SSH to a server, and do not run `make restore`, `make wipe`, or `make backup`.
