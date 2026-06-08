FROM python:3.13.2-slim

WORKDIR /app

ENV NIXPACKS_VERSION=1.39.0
ENV RAILPACK_VERSION=0.6.0

# Install dependencies
RUN apt update && apt install -y debian-keyring debian-archive-keyring apt-transport-https  curl wait-for-it
RUN curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
RUN curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
RUN apt update && apt install -y caddy libpq-dev supervisor gcc python3-dev git
RUN curl -sSL https://nixpacks.com/install.sh | bash
RUN curl -fsSL https://get.docker.com | sh
RUN curl -sSL https://railpack.com/install.sh | sh

# environment variables
ARG COMMIT_SHA
ARG IMAGE_VERSION
ENV COMMIT_SHA=$COMMIT_SHA
ENV IMAGE_VERSION=$IMAGE_VERSION
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/app/.venv

# start the venv (uv)
COPY --from=ghcr.io/astral-sh/uv:0.7.3 /uv /usr/local/bin/uv

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Install python dependencies
COPY ./backend/pyproject.toml ./backend/.python-version ./backend/uv.lock ./
RUN uv sync --locked --no-dev

# Copy app + static files
COPY ./backend/ /app
COPY ./frontend/build/client/ /app/staticfiles

# uvicorn socket-based configuration
RUN mkdir -p /app/uvicorn/
RUN chmod -R 777 /app/uvicorn/

RUN chmod -R a+x /app/scripts/*.sh

# Configure Supervisor
COPY ./docker/app/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY ./docker/app/Caddyfile /etc/caddy/Caddyfile

# Expose necessary ports
EXPOSE 80

RUN mkdir -p /app/logs/caddy
RUN mkdir -p /app/logs/uvicorn

# Start Supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
