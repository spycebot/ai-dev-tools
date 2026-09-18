# Card Catalog — Product Specification

## 1. Overview

**Card Catalog** is a mini Kanban board for a single user to track personal tasks across three fixed stages: To Do, In Progress, and Done. It is a personal productivity tool, not a team collaboration tool — there are no accounts, no sharing, and no multi-board management. The visual design follows the ["living paper"](https://shannonware.com) aesthetic: an old computer-manual look, styled as index cards on aged paper.

This is homework assignment 2 for the [AI Dev Tools Zoomcamp](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp) course, built end-to-end with an AI coding agent.

## 2. Goals / Non-Goals

**Goals**
- Let a single user capture tasks as cards and move them through a simple three-stage workflow.
- Keep the feature set small and well-tested rather than broad.
- Ship in stages: spec → frontend prototype (mocked backend) → backend → integration → real database.

**Non-goals**
- No user accounts, authentication, or multi-user collaboration.
- No multiple boards — there is exactly one board.
- No customizable columns — the three columns are fixed.
- No real-time sync between browser tabs/sessions (a page refresh is sufficient to see the latest state).

## 3. Users

A single, unauthenticated user. The app assumes one person using it locally or via a personal deployment; there is no concept of "who" created or owns a card.

## 4. Core Concepts / Data Model

### Board
There is exactly one board, containing exactly three columns, in this fixed order:
1. **To Do**
2. **In Progress**
3. **Done**

Columns cannot be added, renamed, reordered, or deleted.

### Card
| Field         | Type              | Required | Notes                                                             |
|---------------|-------------------|----------|--------------------------------------------------------------------|
| `id`          | string (UUID)     | yes      | Server-generated, immutable.                                      |
| `title`       | string             | yes      | Short summary of the task. Non-empty.                             |
| `description` | string (multiline) | no       | Free-text details. Empty by default.                              |
| `due_date`    | date (ISO 8601)    | no       | Optional. Used for overdue display (see §5.5).                    |
| `priority`    | enum: `low`, `medium`, `high` | no, default `medium` | Displayed as a tag/badge on the card. |
| `column`      | enum: `todo`, `in_progress`, `done` | yes | Which column the card currently sits in.                |
| `position`    | integer            | yes      | Sort order of the card within its column (lower = higher up).     |
| `created_at`  | datetime           | yes      | Server-generated on creation.                                     |
| `updated_at`  | datetime           | yes      | Server-updated on every change.                                   |

## 5. Functional Requirements

### 5.1 View the board
- On load, the board displays the three columns side by side, each showing its cards in `position` order.
- Each column header shows its name and a live count of the cards it contains (e.g. "To Do (3)").

### 5.2 Create a card
- A visible "add card" control on a column lets the user create a new card directly in that column.
- Only `title` is required at creation time; other fields can be filled in immediately or left for later editing.
- New cards are appended to the end (bottom) of the target column.

### 5.3 Edit a card
- Clicking a card opens it for editing (title, description, due date, priority).
- Edits save explicitly (e.g. a Save action) or on blur — exact interaction is left to the frontend implementation, but there must be no data loss on accidental dismissal without warning if changes are unsaved.

### 5.4 Delete a card
- Each card has a delete control.
- Deleting a card always shows a confirmation prompt before the card is permanently removed. There is no undo and no archive — confirmed deletion is final.

### 5.5 Move and reorder cards
- Cards are moved between columns via **drag-and-drop**.
- Cards can also be manually **reordered within a column** via drag-and-drop.
- Dropping a card updates its `column` and `position` (and the positions of cards displaced around it).
- Cards with a `due_date` in the past that are not in the `done` column are visually flagged as overdue (e.g. a distinct border/text treatment consistent with the paper theme — see §6).

### 5.6 Persistence
- All board state (cards, their fields, column, and position) persists across page reloads.
- In the prototype phase (frontend-only), mocked backend calls should persist to `localStorage` so refresh behavior can still be demonstrated.
- In later phases, persistence is handled by the real backend and database (see §7).

## 6. Look and Feel

The UI follows the **"living paper"** design language (reference implementation: `/var/www/shannonware.com/commercial-shannonware/`):

- **Background:** CSS-only yellowed/aged paper effect — a warm cream base with layered radial gradients (edge vignettes plus a few irregular "age spot" patches). No bitmap images.
- **Typography:** "Special Elite" (typewriter style) for body text and card content; "Share Tech Mono" for data/meta labels (counts, dates, ids).
- **Color palette:**
  - Blueprint blue `#18385a` — primary/structural elements (headers, borders, column dividers).
  - Annotation amber `#7a5c0a` — secondary notes, priority/overdue accents.
  - Warm cream paper tones for backgrounds, dark ink tones for primary text (both colors should read as ink on paper, not as light-emitting UI chrome).
- **Motif:** Cards should read as physical index cards on a shared workspace/desk — subtle shadows, slightly uneven edges or rotation are welcome touches but must not hurt usability (contrast, click targets, readability).
- Both column layout and interactions (drag-and-drop, confirmations) must stay fully usable — the paper aesthetic is a skin, not a constraint on core UX quality.

## 7. Technical Approach

### 7.1 Tech stack
- **Frontend:** React + Vite (Node.js tooling). Drag-and-drop via a library such as `@dnd-kit`.
- **Backend:** Python, FastAPI, managed with `uv`.
- **Database:** SQLite for development; the backend must remain database-agnostic (via SQLAlchemy) so it can be pointed at PostgreSQL later without application code changes.
- **API contract:** an `openapi.yaml` will define the REST contract between frontend and backend before the backend is implemented.

### 7.2 Build phases (per `AGENTS.md`)
This project is built stepwise, with a commit + push to GitHub after each completed step:
1. **Product specification** — this document.
2. **Frontend prototype** — React app in `frontend/`, backend calls centralized in one module and mocked (backed by `localStorage`), full interactivity for create/edit/delete/move/reorder.
3. **Backend** — FastAPI app, tests written first, mock in-memory/data store initially, matching `openapi.yaml`.
4. **Connect frontend and backend** — swap the mocked backend module for real HTTP calls to the FastAPI service.
5. **Database** — swap the backend's mock store for SQLAlchemy models backed by SQLite, keeping the code database-agnostic.

## 8. Testing
- Backend endpoints are covered by tests written before their implementation (TDD-style), per `AGENTS.md`/homework guidance.
- Frontend interactivity (create, edit, delete with confirmation, drag-and-drop move/reorder, overdue flagging, live counts) should be manually verified against this spec at each phase, and covered by automated tests where practical.

## 9. Open Questions / Future Ideas (explicitly out of scope for now)
- Multiple boards or shared/multi-user boards.
- Custom columns.
- Search/filtering, labels/tags beyond priority.
- Card archiving instead of hard deletion.

## 10. Deployment & Operations (Homework 3)

This is homework assignment 3 for the AI Dev Tools Zoomcamp: testing, containerizing, and deploying the app built in homework 2. Scope per `AGENTS.md` / the [Module 3 assignment](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/03-deployment/01-test-containerize-and-deploy-an-ai-assisted-app.md).

### 10.1 Cloud platform: AWS

The course material deploys to AWS; other platforms discussed (Render, Fly.io, Railway) are themselves built on top of AWS/GCP and mainly trade operational convenience (automatic TLS, managed Postgres backups, zero-downtime deploys out of the box) for reduced control over the underlying primitives. AWS was chosen deliberately — the added setup work (VPC, security groups, IAM, ALB) is itself the job-relevant skill being practiced, ahead of an AWS certification goal. See the README's "Requirements Discussion" note for the full reasoning.

### 10.2 Infrastructure

| Concern | Choice |
|---|---|
| Container hosting | **ECS Fargate** — serverless containers, no EC2 instances to manage |
| Database | **RDS Postgres** (managed) — production replaces SQLite entirely |
| Container images | **ECR** — one repository per service (frontend, backend) |
| CI/CD → AWS auth | **GitHub Actions OIDC** assuming an AWS IAM role — no long-lived AWS access keys stored in GitHub secrets |
| Load balancing / TLS | One Application Load Balancer, one target group — the backend Fargate service serves the built frontend (see §10.3), so there's a single origin and no path-based routing to configure |
| Environments | **Lightweight staging + production**: one RDS instance hosting two databases (`staging_db`, `prod_db`), one ECS cluster running two low-cost Fargate services (`card-catalog-staging`, `card-catalog-prod`) |
| Secrets | **AWS Secrets Manager** — `AUTH_PASSWORD_HASH`, `AUTH_SECRET_KEY`, `DATABASE_URL` per environment, injected into the ECS task definition as container secrets (not baked into images or stored in GitHub) |
| Migrations | **Alembic**, driven off the existing SQLAlchemy models in `backend/app/orm.py`; `deploy.yml` runs `alembic upgrade head` against the target environment's database before/as part of the service update |

### 10.3 Containerization
- Multi-stage `Dockerfile` for the backend: build stage compiles the frontend (`npm run build`) and installs Python deps, runtime stage is a slim Python image that serves the API under `/api` **and** the built frontend static files (FastAPI mounts `frontend/dist/`) — one image, one container, one origin, matching the current dev setup's no-CORS/same-origin design.
- `docker-compose.yml` for local dev/integration testing, running Postgres locally (not SQLite) so local behavior matches production.
- SQLite remains for quick local iteration outside Docker if desired, but the Dockerized/CI/staging/production path uses Postgres end-to-end, per the "must be able to switch to PostgreSQL in production" requirement from `AGENTS.md`.

### 10.4 Testing
- `tests/integration/` — exercises a real (Postgres) database, Alembic migrations, authentication, and full frontend→backend workflows via the built container. Must stay fast enough to run on every push.
- Existing unit test suites (`backend/tests/`) continue to run against the in-memory and SQLite stores as today.
- **Post-deploy smoke test** (staging and production, after each deploy): `GET /health`, then a login → `GET /api/cards` round trip against the live environment. Failure fails the deploy job and triggers rollback (see §10.5).

### 10.5 CI/CD
- `.github/workflows/ci.yml` — lint, unit tests, integration tests as merge gates on every push/PR.
- `.github/workflows/deploy.yml` — on merge to `main`: build image, push to ECR (tagged with the commit SHA), run Alembic migrations against `staging_db`, deploy to the staging ECS service, run the smoke test against staging; on success, repeat migrate+deploy+smoke-test against production. **Rollback:** if a deploy's smoke test fails, `deploy.yml` re-points the ECS service at the previous commit SHA's image tag (the last tag that passed its own smoke test) instead of leaving the failing deploy live; this is a redeploy of a known-good image, not a database rollback — Alembic migrations are expected to be additive/backward-compatible so an old image can still run against a migrated schema.

### 10.6 Documentation
- `docs/testing.md`, `docs/deployment.md`, `docs/release-process.md` — required deliverables, written as each corresponding piece is built.
