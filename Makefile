.PHONY: run test lint format docker-up docker-down install install-dev clean eval test-all

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

run:
	streamlit run src/web_app/app.py --server.port=8501

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ evals/ -v --cov=src --cov-report=html --cov-report=term-missing

test-unit:
	pytest tests/unit/ -v --tb=short

test-integration:
	pytest tests/integration/ -v --tb=short

eval:
	pytest evals/ -v --tb=short

test-all:
	pytest tests/ evals/ -v --tb=short

lint:
	ruff check src/ tests/ evals/
	ruff format --check src/ tests/ evals/

format:
	ruff check --fix src/ tests/ evals/
	ruff format src/ tests/ evals/

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	rm -rf htmlcov .coverage .mypy_cache .ruff_cache
