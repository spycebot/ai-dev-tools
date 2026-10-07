# Deployment

Card Catalog runs on AWS in `eu-north-1` (Stockholm), as two environments on
one EC2 host, backed by one managed RDS PostgreSQL instance:

| Environment | URL | Database |
|---|---|---|
| Production | https://cards.terzotech.net | `card_catalog_prod` (user `cc_prod`) |
| Staging | https://staging.cards.terzotech.net | `card_catalog_staging` (user `cc_staging`) |

Both run the same container image (built from the root [`Dockerfile`](../Dockerfile));
only their environment files differ.

## Architecture

```text
                Cloudflare DNS (DNS only, no proxy)
       cards.terzotech.net ─┐   ┌─ staging.cards.terzotech.net
                            ▼   ▼
              Elastic IP 13.48.77.37 — EC2 t3.small (Ubuntu, Docker)
              security group: 80, 443 open; 22 from the owner's IP only
 ┌──────────────────────────────────────────────────────────────────┐
 │  caddy  :80/:443   Let's Encrypt TLS, HTTP→HTTPS, HSTS            │
 │    ├── cards.terzotech.net          → prod:8000                  │
 │    └── staging.cards.terzotech.net  → staging:8000               │
 │  prod     card-catalog:<sha>   env: /srv/card-catalog/prod.env    │
 │  staging  card-catalog:<sha>   env: /srv/card-catalog/staging.env │
 └──────────────────────────────────────────────────────────────────┘
                            │ 5432, TLS (sslmode=require)
                            ▼
      RDS PostgreSQL 17.11 — db.t4g.micro, 20 GB gp3, encrypted, private
      security group: 5432 only from the EC2 instance's security group
```

| Concern | Choice | Why |
|---|---|---|
| Compute | One EC2 `t3.small` running Docker Compose | A dedicated box, so the Docker daemon never shares a host with the owner's other live sites (see the README's Challenges notes). |
| Database | **RDS PostgreSQL 17** (managed), one instance, two databases | Meets "managed database" with automated backups (7 days), patching and encryption. Free-tier instance class. Two databases + two login roles keep staging unable to read or write production data. |
| TLS + routing | Caddy 2 in a container | Obtains and renews Let's Encrypt certificates on its own; one small config file ([`deploy/Caddyfile`](../deploy/Caddyfile)). |
| Static IP | Elastic IP `13.48.77.37` | The DNS records must not break when the instance is stopped and started. |
| DNS | Cloudflare, **DNS only** (grey cloud) | With Cloudflare's proxy on, Let's Encrypt can't validate the origin, and Cloudflare's free certificate doesn't cover the two-level `staging.cards` name. |
| Secrets | `prod.env` / `staging.env` on the host, mode `600` | One host, one operator; no secret is in git, in an image, or in GitHub. The login password is stored only as a bcrypt hash. |
| Migrations | `alembic upgrade head`, run by [`deploy/deploy.sh`](../deploy/deploy.sh) **before** the new version starts | The app never starts against an un-migrated schema. |

This replaces the original ECS Fargate + ALB plan in
[`_docs/specs.md`](../_docs/specs.md) §10 — see the note there for why.

## What's on the server

Everything lives in `/srv/card-catalog/` (owned by `ubuntu`, mode `750`):

| File | Source | Purpose |
|---|---|---|
| `docker-compose.server.yml` | [`deploy/`](../deploy/docker-compose.server.yml) | Caddy + `prod` + `staging` services |
| `Caddyfile` | [`deploy/`](../deploy/Caddyfile) | Hostnames → containers, security headers |
| `deploy.sh` | [`deploy/`](../deploy/deploy.sh) | Deploy, roll back, status (see [release process](./release-process.md)) |
| `smoke.sh` | [`deploy/`](../deploy/smoke.sh) | Post-deploy smoke test, through the real HTTPS front door |
| `set-password.sh` | [`deploy/`](../deploy/set-password.sh) | Set or rotate the login password (prompts, stores only the hash) |
| `images.env` | written by `deploy.sh` | Current and previous image for each environment |
| `prod.env`, `staging.env` | created once by hand, mode `600` | `DATABASE_URL`, `AUTH_PASSWORD_HASH`, `AUTH_SECRET_KEY`, `AUTH_COOKIE_SECURE=true`, `CORS_ORIGINS` |

RDS admin credentials and the per-environment database URLs are kept in
`~/.card-catalog/` (mode `600`), outside the web-facing directory.

## Day-to-day operations

```bash
cd /srv/card-catalog
./deploy.sh status                                  # which image each environment runs
docker compose --env-file images.env -f docker-compose.server.yml logs -f prod
./smoke.sh https://cards.terzotech.net              # re-run the smoke test any time
./set-password.sh                                   # rotate the login password (both envs)
```

Normal releases don't happen here by hand: merging to `main` triggers
`.github/workflows/deploy.yml`. See [`release-process.md`](./release-process.md)
for the pipeline, manual deploys and rollback.

## Rebuilding from scratch

The order the environment was first stood up in, for disaster recovery or a
second copy:

1. **EC2**: Ubuntu, Docker Engine with the Compose plugin, IAM role
   `card-catalog-ec2` attached (policy: `card-catalog-deployer` — RDS/EC2
   create-and-describe only, no deletes).
2. **Networking**: allocate an Elastic IP and associate it; open TCP 80/443
   (and UDP 443) on the instance security group.
3. **RDS**: a security group allowing 5432 from the instance's security
   group only; a DB subnet group over the default VPC subnets; then
   `aws rds create-db-instance` — `postgres` 17.11, `db.t4g.micro`, 20 GB
   gp3, `--no-publicly-accessible`, `--storage-encrypted`,
   `--backup-retention-period 7`, `--deletion-protection`.
4. **Databases**: as the RDS admin user, `CREATE ROLE cc_prod LOGIN ...`,
   `CREATE DATABASE card_catalog_prod OWNER cc_prod`, the same for staging,
   then `REVOKE ALL ON DATABASE ... FROM PUBLIC` on both.
5. **DNS**: two `A` records → the Elastic IP, Cloudflare proxy **off**.
6. **Host**: copy `deploy/*` to `/srv/card-catalog/`, write `prod.env` and
   `staging.env` (mode `600`, a different `AUTH_SECRET_KEY` each), run
   `./set-password.sh`, then deploy an image with `./deploy.sh deploy`.

## Cost

| Item | Monthly (approx.) |
|---|---|
| EC2 `t3.small` + 20 GB disk | ~$17 |
| Public IPv4 (Elastic IP, attached) | ~$3.60 |
| RDS `db.t4g.micro`, 20 GB | $0 on the free tier (~$14 after) |
| Data transfer, Let's Encrypt, Cloudflare DNS | ~$0 |
