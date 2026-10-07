# Release process

Every change reaches production the same way: a pull request, green CI, a
merge to `main`, then an automatic staging → production rollout with smoke
tests and automatic rollback. Nobody deploys by hand in the normal case.

## The path of a change

```text
branch ──► pull request ──► CI (4 required checks) ──► merge to main
                                                            │
                         .github/workflows/deploy.yml  ◄────┘
                                     │
   ci (again, on the merge commit) ──► build + push ghcr.io/spycebot/card-catalog:<sha>
                                     │
                                     ▼
   staging:     migrate ─► switch ─► smoke (server) ─► smoke (outside)
                   any failure ⇒ automatic rollback, production never starts
                                     │
                                     ▼
   production:  migrate ─► switch ─► smoke (server) ─► smoke (outside)
                   any failure ⇒ automatic rollback
```

1. **Open a pull request.** `main` is protected: no direct pushes (admins
   included), no force pushes, and the branch must be up to date with `main`.
2. **CI must pass.** [`ci.yml`](../../.github/workflows/ci.yml) runs four
   required checks (`lint`, `unit-tests`, `integration-tests`, `container`);
   details in [`testing.md`](./testing.md#ci).
3. **Merge.** That push to `main` starts
   [`deploy.yml`](../../.github/workflows/deploy.yml), which re-runs the same
   CI on the merge commit before building anything.
4. **Build.** One image per commit, tagged with the full commit SHA (plus a
   moving `main` tag), pushed to GitHub Container Registry. Staging and
   production run byte-for-byte the same image.
5. **Staging, then production.** Each deploy job:
   1. assumes the `card-catalog-github-deploy` AWS role through GitHub OIDC
      (short-lived credentials, usable only from the `staging` and
      `production` GitHub environments, only on `main`);
   2. sends one AWS Systems Manager command to the EC2 host
      ([`deploy/ssm-run.sh`](../deploy/ssm-run.sh)), which syncs the
      `deploy/` files from that exact commit and runs
      [`deploy/deploy.sh`](../deploy/deploy.sh);
   3. `deploy.sh` pulls the image, runs `alembic upgrade head` against that
      environment's database, swaps the container, waits for its health
      check, and runs [`deploy/smoke.sh`](../deploy/smoke.sh) through the real
      HTTPS front door;
   4. the job then runs `smoke.sh` again from the GitHub runner, from outside
      AWS, against the public URL.

   Production only starts after staging has passed both smoke tests.

## Smoke test

[`deploy/smoke.sh`](../deploy/smoke.sh) runs after every deploy and rollback:

| Check | Proves |
|---|---|
| `GET /health` returns `{"status":"ok"}` | the app process is up behind Caddy, with a valid certificate |
| `GET /` contains `<title>Card Catalog</title>` | the built frontend is being served |
| `GET /api/cards` without a session returns `401` | the API is up and still password-gated |
| `POST /api/login` with a wrong password returns `401` (or `429` once the per-IP rate limit kicks in) | the auth path works end to end (bcrypt hash loaded, rate limiter up) |

It deliberately doesn't log in: the real password isn't stored anywhere a
script could use it. Authenticated workflows are covered before deploy, by
the integration tests and the CI container smoke test.

## Rollback

### Automatic

- **Server-side failure** (image won't start, health check fails, or the
  server-side smoke test fails): `deploy.sh` immediately switches the
  environment back to the image it was running before, re-runs the smoke
  test, and exits non-zero, failing the GitHub job.
- **Outside smoke test fails** after a "successful" server-side deploy: the
  job runs `deploy.sh rollback` for that environment.
- **Staging fails:** production is never touched.

### Manual

From GitHub: **Actions → Deploy → Run workflow**, choose `rollback` and the
environment. Or, on the server:

```bash
cd /srv/card-catalog
./deploy.sh status               # current and previous image per environment
./deploy.sh rollback prod        # switch prod to its previous image + smoke test
./deploy.sh rollback prod        # run again to undo the rollback
```

To pin a specific older build: `./deploy.sh deploy prod ghcr.io/spycebot/card-catalog:<full-sha>`.

### Database changes and rollback

A rollback swaps the **image**, never the **database**. Migrations only
ever move forward, so every migration must keep the previous release
working:

- **Add, don't change.** Add new columns as nullable or with a default;
  add new tables freely.
- **Remove in two releases.** Stop using a column in release N; drop it in
  release N+1, once N is known good.
- **Rename = add + backfill + switch + drop**, across releases.

If a migration itself is the problem, write a new forward migration that
fixes it. RDS keeps 7 days of automated backups, so restoring to a point in
time (to a new instance) is the last resort for data loss, not the rollback
path.

## Configuration and secrets changes

Secrets aren't part of a release. They live in `/srv/card-catalog/prod.env`
and `staging.env` on the host:

- **Login password:** `/srv/card-catalog/set-password.sh` (prompts, stores
  only the bcrypt hash, restarts the app containers).
- **Anything else** (e.g. `AUTH_SECRET_KEY`): edit the file, then
  `docker compose --env-file images.env -f docker-compose.server.yml up -d --force-recreate --no-deps prod`.
  Changing `AUTH_SECRET_KEY` logs everyone out.

## Checklist for a release with a migration

- [ ] Migration is additive or backward compatible (see above)
- [ ] `alembic upgrade head` tested locally on Postgres (`docker compose up` runs it)
- [ ] Integration tests cover the new schema
- [ ] After merge, staging deploy green before production starts
- [ ] Spot-check the feature on https://staging.cards.terzotech.net
