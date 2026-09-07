FROM node:24-alpine

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml /app/
COPY packages/shared/package.json /app/packages/shared/package.json
COPY apps/web/package.json /app/apps/web/package.json
RUN pnpm install --frozen-lockfile=false

COPY packages/shared /app/packages/shared
COPY apps/web /app/apps/web

EXPOSE 3000

CMD ["sh", "-c", "pnpm --dir apps/web build && pnpm --dir apps/web exec next start -H 0.0.0.0 -p ${PORT:-3000}"]
