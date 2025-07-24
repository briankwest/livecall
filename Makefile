.PHONY: help build up down logs shell clean init dev prod

help:
	@echo "Available commands:"
	@echo "  make init    - Initialize project (copy .env, create directories)"
	@echo "  make build   - Build all Docker images"
	@echo "  make up      - Start all services"
	@echo "  make down    - Stop all services"
	@echo "  make dev     - Start in development mode with hot reload"
	@echo "  make logs    - View logs from all services"
	@echo "  make shell   - Open shell in backend container"
	@echo "  make clean   - Remove volumes and containers"

init:
	@echo "Initializing project..."
	@cp -n .env.example .env || true
	@mkdir -p logs/backend logs/nginx logs/frontend
	@echo "Project initialized. Please update .env with your credentials."

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

logs:
	docker-compose logs -f

shell:
	docker-compose exec backend /bin/bash

shell-db:
	docker-compose exec postgres psql -U postgres -d livecall

clean:
	docker-compose down -v
	rm -rf logs/*

restart:
	docker-compose restart

status:
	docker-compose ps

migrate:
	docker-compose exec backend python scripts/migrate.py

test:
	docker-compose exec backend pytest