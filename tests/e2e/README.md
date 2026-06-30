# E2E Tests

These Playwright tests target the real local stack started by Docker Compose.

Host-run option:

```bash
pnpm install
E2E_BASE_URL=http://localhost:3000 E2E_API_BASE_URL=http://localhost:8000 pnpm --filter @english-ai-writing/e2e test
```

If the local Playwright browser cache is missing the exact Chromium build, either run
`pnpm --filter @english-ai-writing/e2e exec playwright install chromium` or point the
test runner at an existing Chrome/Chromium binary:

```bash
E2E_BASE_URL=http://localhost:3000 \
E2E_API_BASE_URL=http://localhost:8000 \
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="/absolute/path/to/Chrome" \
pnpm --filter @english-ai-writing/e2e test
```

Docker-run option:

```bash
docker compose --profile e2e up -d web-e2e
docker compose --profile e2e run --rm e2e
```

The Docker option starts `web-e2e` with `NEXT_PUBLIC_API_BASE_URL=same-origin` and `API_PROXY_TARGET=http://api:8000`, so the browser inside the Playwright container uses same-origin `/api` requests while Next.js proxies them to the API service.

Required local services:

- web: `http://localhost:3000`
- api: `http://localhost:8000`
- auth: `http://localhost:9000`
- PostgreSQL, Redis, LanguageTool and a configured LLM provider for marking scenarios

The current smoke specs cover admin, teacher and student login routing, the shared app shell, teacher rubric/task controls, admin AI status/account controls and student task entry. Extend `specs/uat-flow.spec.ts` with the full UAT scenarios as UI selectors settle.
