# Foxpip — AI-Assisted English Writing & Assessment Platform

[![Next.js](https://img.shields.io/badge/Next.js-frontend-000000)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688)](https://fastapi.tiangolo.com/)
[![Status](https://img.shields.io/badge/status-in--development-yellow)]()

An AI-assisted platform for schools to author writing tasks, run practice and exam sessions, and grade student writing with LLM-assisted marking and human teacher review.

**Status: actively in development, started June 2026.** The repository contains generic demo data only — tender documents, UAT exports, generated account lists, internal reports, and real API credentials are intentionally excluded.

## Overview

Foxpip is a school writing-assessment platform split into a teacher/admin workflow and a student writing workflow. Teachers author writing tasks and rubrics, publish assignments to classes, review AI-generated marking before releasing it to students, and export class-level reports. Students write in practice or exam mode with autosaved drafts, real-time grammar suggestions, and AI-assisted feedback and rewriting once their work is marked.

The backend is a FastAPI service with its own authentication service, background marking worker, and a self-hosted LanguageTool container for grammar checking; the frontend is a Next.js application. AI marking is provider-agnostic — the LLM adapter supports OpenAI-compatible endpoints, DeepSeek, Qwen, Doubao, and MiniMax.

## Features

**Teacher / school admin**
- Rubric authoring, duplication, and editing, with AI-assisted question/task generation
- Assignment publishing to classes
- AI-assisted marking queue with a run / retry / human-review / release workflow before feedback reaches students
- Class dashboards and CSV report export
- School, class, and user administration, including CSV user import

**Student**
- Practice and exam writing modes, with exam events (e.g. focus loss, paste) recorded during timed sessions
- Autosaved drafts, separate from final submission
- Real-time grammar and spelling suggestions at word, sentence, and paragraph level (LanguageTool-backed)
- Personalized practice generation and AI feedback/rewriting support
- Submission history and released-feedback viewing

**Platform**
- Local email/password authentication service (`apps/auth`)
- Optional MiniMax integration for read-aloud (TTS) and image generation
- Dockerized stack: PostgreSQL, Redis, auth service, LanguageTool, API, background marking worker, and the Next.js web app

## Tech stack

- **Frontend:** Next.js (App Router) + TypeScript + Tailwind CSS
- **Backend:** FastAPI + SQLAlchemy (async) + Alembic + PostgreSQL + Redis
- **Grammar checking:** self-hosted LanguageTool (no API key required)
- **AI marking / LLM:** pluggable provider adapter — OpenAI-compatible, DeepSeek, Qwen, Doubao, MiniMax
- **Monorepo:** pnpm workspaces (`apps/web`, `apps/api`, `apps/auth`, `packages/shared`)
- **Infra:** Docker Compose, Alembic migrations

## Requirements

- Docker Desktop 4.30+ or Docker Engine with Docker Compose v2
- At least 4 GB of memory available to Docker (6 GB recommended)
- Ports `3000`, `8000`, `8010`, `9000`, `5432`, and `6379` available locally

No local Node.js, Python, PostgreSQL, or Redis installation is required for the Docker setup.

## Installation

```bash
git clone https://github.com/A11MiND/English_Writing.git
cd English_Writing
cp .env.example .env
docker compose up --build -d
docker compose exec api alembic upgrade head
```

Open the application at [http://localhost:3000](http://localhost:3000).

Demo accounts (development defaults — change before any shared or internet-accessible deployment), password `Password123!`:

| Role | Email |
| --- | --- |
| School admin | `admin@school.example` |
| Teacher | `teacher@school.example` |
| Pupil | `student@school.example` |

Verify the stack is healthy:

```bash
docker compose ps
curl http://localhost:8000/api/health
curl -I http://localhost:3000/login
```

## AI configuration

Grammar checking works out of the box through the bundled LanguageTool container. AI marking, question generation, and rewriting are optional — set a provider in `.env`:

```dotenv
LLM_PROVIDER=minimax
LLM_MODEL=MiniMax-M3
LLM_BASE_URL=https://api.minimaxi.com/v1
LLM_API_KEY=your-key-here
```

Optional read-aloud and image generation:

```dotenv
MINIMAX_API_KEYS=your-key-here
```

Never commit `.env` or real credentials — only `.env.example` (with empty key fields) is tracked.

## Common operations

```bash
# Tail logs
docker compose logs -f web api auth marking-worker

# Restart
docker compose restart

# Stop, keeping data
docker compose down

# Wipe local data and start clean
docker compose down -v
docker compose up --build -d
docker compose exec api alembic upgrade head
```

For a short-lived public link during a demo:

```bash
cloudflared tunnel --url http://localhost:3000
```

Quick Tunnel URLs are temporary with no uptime guarantee — use a named Cloudflare Tunnel and your own domain for anything longer-lived.

## Project structure

```text
apps/web/       Next.js frontend
apps/api/       FastAPI application and marking worker
apps/auth/      Local authentication service
infra/          Dockerfiles and Alembic migrations
packages/       Shared TypeScript contracts
services/       Grammar and other integration services
workers/        Background worker packages
scripts/dev/    Local setup, reset, smoke-test, and tunnel helpers
```

## Production notes

This is a development platform, not a hardened production deployment. Before any real school or internet-facing use:

- Replace the PostgreSQL, auth-client, and signing secrets
- Replace or remove all demo identities
- Restrict database, Redis, auth, API, and LanguageTool ports to the private network
- Configure HTTPS, backups, monitoring, rate limits, and a stable object store for generated media
- Use a managed secret store instead of environment files
- Review child-data privacy, retention, consent, and school access-control requirements before handling real student data

## License

No open-source license has been granted yet. Add an appropriate `LICENSE` before distributing or accepting external contributions.
