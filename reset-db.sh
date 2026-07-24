#!/bin/bash
echo "⚠️ THIS WILL RESET THE DATABASE AND WIPE OUT ALL DATA ⚠️"
read -p "Are you sure? (Y/N): " -n 1 -r

if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Bye... 👋"
    [[ "$0" = "$BASH_SOURCE" ]] && exit 1 || return 1 # handle exits from shell or function but don't exit interactive shell
fi

echo ""

echo "Deleting all user created services..."
docker service rm $(docker service ls -q --filter label=dky-managed=true)  2>/dev/null

echo "Waiting for all containers related to services to be removed..."
while [ -n "$(docker ps -a | grep "srv-prj_" | awk '{print $1}')" ]; do \
  sleep 2; \
done

echo "Deleting volumes..."
docker volume rm $(docker volume ls -q --filter label=dky-managed=true) 2>/dev/null

echo "Deleting networks..."
docker network rm $(docker network ls -q --filter label=dky-managed=true) 2>/dev/null

echo "Running a system prune..."
docker system prune -f --volumes

echo "Stopping temporal server..."
docker compose -f ./docker/docker-compose.yaml down dky-temporal-server
docker stack rm dockyard

echo "Flushing temporalio database..."
docker exec -it $(docker ps -qf "name=dky-db") psql -U postgres -c "DROP database temporal;"

echo "Restarting temporal-admin-tools to configure temporal server..."
docker stack deploy --with-registry-auth --compose-file ./docker/docker-stack.yaml dockyard

echo "Restarting temporalio server..."
docker compose -f ./docker/docker-compose.yaml up -d dky-temporal-server

echo "Resetting caddy config..."
curl "http://127.0.0.1:2019/load" \
	-H "Content-Type: application/json" \
	-d @docker/proxy/default-caddy-config-dev.json

echo "Flushing the main app database..."
docker exec -it $(docker ps -qf "name=dky-db") psql -U postgres -c "DROP database dockyard;"
docker exec -it $(docker ps -qf "name=dky-db") psql -U postgres -c "CREATE database dockyard;"
source ./backend/.venv/bin/activate && cd backend && alembic upgrade head && cd ..


echo -e "Create the first user from the onboarding screen at \x1b[96mhttp://localhost:5173/onboarding\x1b[0m"
echo "RESET DONE ✅"
