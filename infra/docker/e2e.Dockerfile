FROM mcr.microsoft.com/playwright:v1.53.0-noble

WORKDIR /e2e

RUN corepack enable

COPY tests/e2e/package.json /e2e/package.json
RUN pnpm install --frozen-lockfile=false

COPY tests/e2e /e2e

ENV E2E_BASE_URL=http://web-e2e:3000

CMD ["pnpm", "test"]
