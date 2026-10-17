# lightweight-auth — SQLite

**Lightweight auth & RBAC for PoC, small services, and agent auth.**
SQLite backend — zero setup, single file, no external services.

---

## Why SQLite

- **Zero setup** — no external DB, no credentials, no migrations to run by hand.
- **Single file** — `data/auth.db` lives next to the app. Backup = copy the file.
- **Fast enough** — for PoC, internal tools, agent auth, small services.
- **Read the whole auth flow in one evening** — no Keycloak, no realm config, no JVM.

---

## When to use this

- PoC or demo that needs auth *today*.
- Internal tool with one instance and a handful of users.
- Agent auth — API keys, OTP, no browser.
- OTP stored plaintext in SQLite for PoC; hash before production use.
- You want to read the code, not configure it.

## When NOT to use this

- Multiple app instances behind a load balancer.
- High write concurrency (many logins per second).
- Compliance-heavy environments (SOC2, HIPAA).

---

## Quick start (local)

```bash
git clone https://github.com/ivatmn/lightweight-auth
cd lightweight-auth

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # optional — defaults work out of the box
python main.py