FROM caddy:2.9.1-builder-alpine AS builder
RUN xcaddy build --with github.com/caddy-dns/cloudflare

FROM caddy:2.9.1-alpine

LABEL org.opencontainers.image.source=https://github.com/kuluruvineeth/dockyard

ARG COMMIT_SHA
ENV COMMIT_SHA=$COMMIT_SHA
ARG ENVIRONMENT=dev

RUN apk update && apk add --no-cache curl jq

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
COPY default-caddy-config-${ENVIRONMENT}.json /config/caddy/autosave.json
CMD caddy run --resume
