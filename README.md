# lightweight-auth

**Lightweight auth & RBAC for PoC, small services, and agent auth.**
Alternative to Keycloak when enterprise SSO is overkill.

---

## Why

Keycloak is powerful, but heavy: JVM, memory, realm config, SSO ceremony.
Most projects — PoC, internal tools, small services, agent auth — don't need that.

`lightweight-auth` gives you:
- **Auth** — login, JWT in HttpOnly cookie, anti-brute-force, account lockout.
- **RBAC** — roles, groups, `access_type` (region / program / mega_project / project).
- **Agent auth** — API keys per user, Telegram OTP, no browser required.
- **Minimal footprint** — FastAPI, one process, `docker compose up`.

No realms. No admin console you have to learn. No JVM.

---

## Choose your backend

Two backends, **same API, same architecture, same code layout**.
Pick one, run it, and switch later without rewriting your client code.

| Backend | Branch | Use for | Setup |
|---|---|---|---|
| **SQLite** | [`sqlite`](https://github.com/ivatmn/lightweight-auth/tree/sqlite) | PoC, internal tools, agent auth, small services | Zero — single file, `docker compose up` |
| **PostgreSQL** | [`postgres`](https://github.com/ivatmn/lightweight-auth/tree/postgres) | Real workloads, teams, multi-instance, concurrency | `docker compose up` with a Postgres service |

**Branch model**

- `main` — this page. Overview and comparison. No code.
- `sqlite` — SQLite backend. The recommended starting point.
- `postgres` — PostgreSQL backend. Same API, same handlers, different storage layer.

**Not sure which one to pick?**
Start with `sqlite`. Move to `postgres` when you hit write concurrency,
multiple app instances behind a load balancer, or a team that needs shared storage.
The API surface does not change — only the storage layer and the connection pool.

**Why branches and not folders?**
Branches keep each backend's `docker-compose.yml`, dependencies, and migrations
clean and independent. You clone what you need, not a monorepo with dead code.

---

## When to use

- You need auth for a PoC or internal tool, not enterprise SSO.
- You're building agent auth — API keys, OTP, no browser.
- You want RBAC without deploying Keycloak.
- You want to read the whole auth flow in one evening.

## When NOT to use

- Enterprise SSO (SAML, OIDC federation, multi-tenant).
- Compliance-heavy environments (SOC2, HIPAA) — you'll need audit and policy layers.
- You already have Keycloak and it works.

---

## What's inside

- **FastAPI** — async, typed, OpenAPI out of the box.
- **JWT + HttpOnly cookies** — correct model for web clients, no localStorage.
- **RBAC** — roles with `is_system`, groups with `access_type`, user↔group links.
- **Agent identity** — `api_key` per user, Telegram OTP with expiry.
- **Anti-brute-force** — failed attempt counter, lockout after 5 tries.
- **Two backends** — SQLite (default) and PostgreSQL (branch).

---

## Quick start

### SQLite (recommended for a first run)


### Postgresql 