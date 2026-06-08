#!/bin/bash
set -ex
source $VIRTUAL_ENV/bin/activate
wait-for-it dky.loki:3100 -t 0 -- wait-for-it dky.temporal:7233 -t 0 --
python -m app.temporal.worker
