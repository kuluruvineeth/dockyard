#!/bin/bash
echo "Removing the proxy and the docker-compose stack..."
docker stack rm dockyard && docker compose down --remove-orphans

echo "Scaling down all dockyard services..."
docker service ls --filter "label=dky-managed=true" -q | xargs -P 0 -I {} docker service scale --detach {}=0

echo "Done undeploying the stack"
