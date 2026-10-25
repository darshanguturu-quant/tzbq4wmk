.PHONY: ingest test test-backend test-frontend run build lint

ingest:
	python backend/scripts/ingest_elexon.py

test: test-backend

test-backend:
	pytest backend/tests

test-frontend:
	cd frontend && npm test

run:
	uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

build:
	docker build -t wind-forecast-portal .

lint:
	ruff check backend/
	ruff format --check backend/
