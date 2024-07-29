.PHONY: init-dev
# Install all dependencies in venv and install pre-commit hooks
init-dev:
	@poetry install &&\
	poetry shell &&\
	pre-commit install


.PHONY: alembic-upgrade
# Apply all migrations
alembic-upgrade:
	cd app &&\
	alembic upgrade head


.PHONY: run-hooks
# run pre-commit hooks for all files
run-hooks:
	@poetry run pre-commit run --all-files


# [compose-local]-[BEGIN]
.PHONY: run-local-dev
# Run services for local development
run-local-dev:
		docker compose up --build


.PHONY: run-local-dev-d
# Run services for local development in detach mode
run-local-dev-d:
		docker compose up --build --detach


.PHONY: stop-local-dev
# Stop and remove containers
stop-local-dev:
	docker compose down


.PHONY: d-purge
# Purge all data related with services
d-purge:
		docker compose down --volumes --remove-orphans
# [compose-local]-[END]
