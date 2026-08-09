# Foxpip — English Writing Platform

[![Next.js](https://img.shields.io/badge/Next.js-frontend-000000)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688)](https://fastapi.tiangolo.com/)
[![Status](https://img.shields.io/badge/status-in--development-yellow)]()

An AI-assisted English writing platform for primary-school teachers and pupils. Teachers can create assignments, review submissions, release feedback, and export reports. Pupils can write in a focused editor with word-, sentence-, and paragraph-level language support.

This repository is under active development; see [Production notes](#production-notes) before any real deployment.

## Included

- Teacher, pupil, and school-admin workspaces
- Assignment and rubric workflow
- Practice and exam writing modes
- Real-time spelling, sentence, and paragraph feedback
- AI-assisted marking, tone support, and writing advice
- Read-aloud and image generation adapters for optional MiniMax integration
- CSV/PDF reporting and class-level analysis
- PostgreSQL, Redis, authentication service, LanguageTool, API, worker, and Next.js web app
- Docker Compose installation

The repository contains generic demo data only. Tender documents, UAT exports, generated account lists, internal reports, and real API credentials are intentionally excluded.

## Requirements

- Docker Desktop 4.30+ or Docker Engine with Docker Compose v2
- At least 4 GB of memory available to Docker; 6 GB is recommended
- Ports `3000`, `8000`, `8010`, `9000`, `5432`, and `6379` available locally

No local Node.js, Python, PostgreSQL, or Redis installation is required for the Docker setup.

## Quick start with Docker

```bash
git clone https://github.com/A11MiND/English_Writing.git
cd English_Writing
cp .env.example .env
docker compose up --build -d
docker compose exec api alembic upgrade head
```

Open the application at [http://localhost:3000](http://localhost:3000).

Demo accounts use the password `Password123!`:

| Role | Email |
| --- | --- |
| School admin | `admin@school.example` |
| Teacher | `teacher@school.example` |
| Pupil | `student@school.example` |

These accounts and secrets are development defaults. Change them before any shared or internet-accessible deployment.

## Verify the installation

```bash
docker compose ps
curl http://localhost:8000/api/health
curl -I http://localhost:3000/login
```

The API health response should report the API and Redis checks as `ok`.

## AI configuration

Grammar checking works through the included LanguageTool container and does not require an API key.

AI marking and rewriting are optional. Edit `.env` locally and set an appropriate provider:

```dotenv
LLM_PROVIDER=minimax
LLM_MODEL=MiniMax-M3
LLM_BASE_URL=https://api.minimaxi.com/v1
LLM_API_KEY=your-key-here
```

Optional read-aloud and image generation use:

```dotenv
MINIMAX_API_KEYS=your-key-here
```

Never commit `.env` or real credentials. The repository only tracks `.env.example` with empty API-key fields.

## Common operations

View logs:

```bash
docker compose logs -f web api auth marking-worker
```

Restart the application:

```bash
docker compose restart
```

Stop containers while keeping database data:

```bash
docker compose down
```

Delete all local application data and start clean:

```bash
docker compose down -v
docker compose up --build -d
docker compose exec api alembic upgrade head
```

## Optional temporary public link

For short demonstrations, install `cloudflared` and run:

```bash
cloudflared tunnel --url http://localhost:3000
```

Quick Tunnel URLs are temporary and have no uptime guarantee. Use a named Cloudflare Tunnel and your own domain for a stable deployment.

## Production notes

Before production use:

- Replace the PostgreSQL, OpenAuth client, and signing secrets.
- Replace or remove all demo identities.
- Restrict database, Redis, authentication, API, and LanguageTool ports to the private network.
- Configure HTTPS, backups, monitoring, rate limits, and a stable object store for generated media.
- Use a managed secret store instead of environment files.
- Review child-data privacy, retention, consent, and school access-control requirements.

## Project structure

```text
apps/web/       Next.js frontend
apps/api/       FastAPI application and marking worker
apps/auth/      Local authentication adapter
infra/          Dockerfiles and Alembic migrations
packages/       Shared TypeScript contracts
services/       Language and integration services
workers/        Background worker packages
scripts/dev/    Local setup, reset, smoke-test, and tunnel helpers
```

## License

No open-source license has been granted yet. Add an appropriate `LICENSE` before distributing or accepting external contributions.
