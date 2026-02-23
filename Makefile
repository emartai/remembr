.PHONY: setup install-hooks install-server install-python-sdk install-ts-sdk

setup: install-hooks install-server install-python-sdk install-ts-sdk
	@echo "✓ Remembr setup complete!"

install-hooks:
	pip install pre-commit
	pre-commit install
	@echo "✓ Pre-commit hooks installed"

install-server:
	cd server && pip install -e ".[dev]"
	@echo "✓ Server installed"

install-python-sdk:
	cd sdk/python && pip install -e ".[dev]"
	@echo "✓ Python SDK installed"

install-ts-sdk:
	cd sdk/typescript && npm install
	@echo "✓ TypeScript SDK installed"
