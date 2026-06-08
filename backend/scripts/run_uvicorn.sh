#!/bin/bash
set -ex
wait-for-it dky.loki:3100 -t 0 -- wait-for-it dky.temporal:7233 -t 0 --
source $VIRTUAL_ENV/bin/activate
alembic upgrade head
python -m app.cli create_metrics_cleanup_schedule
python -m app.cli create_system_cleanup_schedule
uvicorn app.main:app --uds /app/uvicorn/uvicorn.sock
