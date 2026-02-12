SHELL := /bin/sh

USE_UV := $(shell if command -v uv >/dev/null 2>&1; then echo "1"; else echo "0"; fi)
RUN := $(if $(filter 1,$(USE_UV)),uv run,)
RUN_DEV := $(if $(filter 1,$(USE_UV)),uv run --group dev,)
RUN_TEST := $(if $(filter 1,$(USE_UV)),uv run --group test,)
RUN_DEV_TEST := $(if $(filter 1,$(USE_UV)),uv run --group dev --group test,)

.PHONY: help black ruff mypy test lint typecheck checkall testall

help:
	@echo "Available targets:"
	@echo "  black      Run black formatter"
	@echo "  ruff       Run ruff with --fix"
	@echo "  mypy       Run mypy type checks"
	@echo "  test       Run pytest"
	@echo "  lint       Run black + ruff"
	@echo "  typecheck  Run mypy (keeps going in composed targets)"
	@echo "  checkall   Run lint + typecheck"
	@echo "  testall    Run pytest with black, ruff and mypy plugins"
	@echo ""
	@echo "Runner: $(if $(RUN),uv run (+ groups),direct)"

black:
	$(RUN_DEV) black .

ruff:
	$(RUN_DEV) ruff check --fix .

mypy:
	$(RUN_DEV) mypy .

test:
	$(RUN_TEST) pytest .

lint: black ruff

typecheck:
	-$(MAKE) mypy

checkall: lint typecheck

testall:
	$(RUN_DEV_TEST) pytest --black --ruff --mypy .
