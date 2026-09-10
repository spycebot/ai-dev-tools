# Card Catalog

A mini Kanban board for tracking personal tasks across three stages — **To Do**, **In Progress**, and **Done** — styled after the ["living paper"](https://shannonware.com) design language: an old computer-manual look built from index cards on aged paper.

This is homework assignment 2 for the [AI Dev Tools Zoomcamp](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp) course. The entire application — spec, frontend, backend, and database — is being built end-to-end with an AI coding agent (Claude Code), in stepwise fashion, with a commit + push after each completed step.

The full product specification lives at [`_docs/specs.md`](./_docs/specs.md). Read that document for complete functional requirements, the data model, and design details — this README focuses on what the app is, how it's built, and how to run it.

## Status

This project is being built in five stages. Current progress:

- [x] **1. Product specification** — see [`_docs/specs.md`](./_docs/specs.md)
- [x] **2. Frontend prototype** (mocked backend) — in `frontend/`
- [ ] **3. Backend** (FastAPI, mock data store)
- [ ] **4. Connect frontend and backend**
- [ ] **5. Database** (SQLite, SQLAlchemy)

The backend does not exist yet — sections below covering it will be filled in as stages 3–5 land.

## Feature Summary

- Single user, no login, one board, three fixed columns (no custom columns).
- Cards have a title (required), description, due date, and priority (low/medium/high).
- Create, edit, and delete cards (delete requires confirmation — no undo).
- Drag-and-drop to move cards between columns and to reorder cards within a column.
- Column headers show a live card count.
- Cards past their due date (and not in Done) are visually flagged as overdue.

See [`_docs/specs.md`](./_docs/specs.md) for full detail on each of these.

## Tech Stack

| Layer            | Choice                                            | Notes                                                                 |
|-------------------|----------------------------------------------------|------------------------------------------------------------------------|
| Frontend          | React + Vite (Node.js)                            | Drag-and-drop via a library such as `@dnd-kit`.                        |
| Backend           | Python + FastAPI, managed with `uv`               | Tests written before implementation.                                  |
| API contract      | `openapi.yaml`                                    | Source of truth between frontend and backend.                         |
| Database (dev)    | SQLite                                             | Accessed through SQLAlchemy so the backend stays database-agnostic.   |
| Database (future) | PostgreSQL                                         | Swap-in target once the app is stable, no application code changes.   |
| Styling           | Custom CSS ("living paper" theme)                 | Special Elite (body) and Share Tech Mono (data/labels) fonts, aged-paper CSS background, blueprint blue (`#18385a`) and annotation amber (`#7a5c0a`) accent colors. |

## Project Structure

```
02-ai-assisted-full-stack-app/
├── AGENTS.md          # Instructions for the AI coding agent building this project
├── README.md          # This file
├── _docs/
│   └── specs.md       # Full product specification
├── frontend/          # React + Vite app (prototype, mocked backend)
│   └── src/
│       ├── api/cards.js       # Centralized mock "backend" (localStorage-backed)
│       ├── components/        # Column, CardItem, CardEditor
│       ├── App.jsx            # Board state, drag-and-drop wiring
│       ├── App.css            # "Living paper" theme (layout + components)
│       └── index.css          # Aged-paper background, fonts, color tokens
└── backend/           # (to be added in stage 3) FastAPI app
```

## Installation

```bash
cd frontend
npm install
```

## Running the App

The frontend is currently a **prototype with a mocked backend** — there is no real server yet. All "backend" calls are centralized in `frontend/src/api/cards.js`, which persists board state to the browser's `localStorage` so data survives a page refresh. This module is the only file that will need to change in stage 4 when it's swapped for real HTTP calls to the FastAPI backend.

```bash
cd frontend
npm run dev
```

This starts the Vite dev server at **http://localhost:5173**.

## Running Tests

_Not yet available. Backend endpoints will be developed test-first (see `_docs/specs.md` §8); the test command will be documented here once the backend exists._

## Challenges & Notes

Notes on anything non-obvious encountered while building this project, kept up to date as work progresses:

- **Git lives one level up.** This project's `.git` repository and `.gitignore` live in the parent directory (`/var/www/terzotech.net/ai-dev-tools/`), not in this folder. All git operations (status, add, commit, push) for this project are run from, or relative to, that parent directory rather than from `02-ai-assisted-full-stack-app/` itself.
- **AGENTS.md takes precedence over the published homework instructions** where the two differ (for example, the homework assumes `.gitignore`/`.git` live inside the project folder — here they live in the parent repo instead).
- **Spec-first workflow.** Before any code was written, the product specification was developed interactively (feature scope, data model, interaction choices, and the app name "Card Catalog" were all decided through a Q&A session) and captured in `_docs/specs.md`, per the course's spec-first methodology.
- **Mocked backend is one module, by design.** `frontend/src/api/cards.js` is the single seam between the UI and "the backend." Every function returns a `Promise` and mirrors what a real REST call will look like, so stage 4 (connecting to FastAPI) should only require rewriting that one file, not the components that call it.
- **dnd-kit's `useSortable` spreads `role="button"` onto the draggable element.** This meant a naive "click the element containing this text" test helper matched the outer card instead of the inner clickable content during manual browser verification. Not an app bug, but worth knowing if you write UI tests against these cards — target `.card-content` specifically, not the card root.

## Course Context

Built for [Homework 2: Build and Ship an AI-Assisted Full-Stack App](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/cohorts/2026/02-development/homework.md) of the AI Dev Tools Zoomcamp.
