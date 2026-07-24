<h1 align="center">Dockyard</h1>

<p align="center"><b>Your own PaaS — deploy images, git repos, and compose stacks on machines you control.</b></p>

Dockyard is a self-hosted platform-as-a-service built on Docker Swarm. Point it at a
Docker image, a git repository, or a compose file and it deploys, exposes over HTTPS,
scales, and monitors it — with preview environments per pull request, a browser
webshell into any container, and workspace-based access control.

## Stack

- FastAPI · SQLAlchemy 2 (async) · Alembic · Pydantic v2
- Temporal workflows for durable deployments
- Docker Swarm · Caddy proxy
- PostgreSQL 16 · Valkey · Loki · Fluentd · Grafana
- React Router 7 · Vite · Tailwind · shadcn/ui · xterm.js

## Quick start

Prerequisites: Docker (Swarm-capable), Python 3.13+ with [uv](https://docs.astral.sh/uv/), Node 20 with [pnpm](https://pnpm.io), `make`.

```bash
make setup     # init swarm, create the overlay network, install deps
make dev       # start the full stack + frontend dev server
make migrate   # apply database migrations
```

Open **http://localhost:5173** and create your first user on the onboarding screen.
