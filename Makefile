.PHONY: init-dev
# Install all dependencies in venv and install pre-commit hooks
init-dev:
	@poetry install &&\
	poetry shell &&\
	pre-commit install


.PHONY: run-hooks
# run pre-commit hooks for all files
run-hooks:
	@poetry run pre-commit run --all-files
