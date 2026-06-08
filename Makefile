.DEFAULT_GOAL := help
help: ### Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

setup: ### Initial setup of the project
	echo 'Creating a virtual env...'
	echo 'initializating docker swarm'
	@if docker info --format '{{.Swarm.LocalNodeState}}' | grep -qw "active"; then \
		if docker info --format '{{.Swarm.ControlAvailable}}' | grep -qw "true"; then \
			echo "Swarm is enabled and this node is a manager, skipping swarm initialization 👍"; \
		else \
			echo "❌ ERROR: Swarm is enabled, but this node is not a manager. Dockyard needs be installed on a docker swarm manager. ❌" >&2; \
			echo "To promote this node to a manager, run: docker node promote <node_name>" >&2; \
			echo "You can check the node name by running: docker node ls" >&2; \
			exit 1; \
		fi \
	else \
		docker swarm init; \
	fi
	@if docker network ls | grep -qw "dockyard"; then \
    	echo "Dockyard network already exists, skipping"; \
	else \
    	docker network create --attachable --driver overlay --label dky.stack=true dockyard; \
	fi
	@command -v uv >/dev/null 2>&1 || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	cd backend/ && uv sync --locked
	pnpm install --frozen-lockfile
	chmod -R a+rx ./docker/temporalio/*.sh

deploy-temporal-ui:
	docker stack deploy --with-registry-auth --detach=false --compose-file docker-stack.prod-temporal-ui.yaml dockyard-temporal-ui

stop-temporal-ui:
	docker stack rm dockyard-temporal-ui

migrate: ### Run db migration
	cd backend && uv run alembic upgrade head

dev: ### Start the DEV server
	pnpm run --recursive --include-workspace-root --parallel dev

dev-api: ### Start the DEV server without the frontend
	pnpm run  --filter='!frontend' --recursive --include-workspace-root --parallel dev


reset-db: ### Wipe out the database and reset the application to its initial state
	chmod a+x reset-db.sh
	./reset-db.sh
