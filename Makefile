# ePub to Audiobook - Makefile
# Convenience commands for development and deployment

.PHONY: help build run stop logs shell clean dev web

# Default target
help:
	@echo "ePub to Audiobook Converter"
	@echo ""
	@echo "Docker commands:"
	@echo "  make build    - Build Docker image"
	@echo "  make run      - Start container (detached)"
	@echo "  make stop     - Stop container"
	@echo "  make logs     - View container logs"
	@echo "  make shell    - Open shell in container"
	@echo "  make clean    - Remove container and image"
	@echo ""
	@echo "Development commands:"
	@echo "  make dev      - Run Flask dev server locally"
	@echo "  make web      - Run with gunicorn locally"
	@echo "  make install  - Install Python dependencies"
	@echo ""

# Docker commands
build:
	docker-compose build

run:
	docker-compose up -d
	@echo ""
	@echo "Started! Open http://localhost:5000"

stop:
	docker-compose down

logs:
	docker-compose logs -f

shell:
	docker-compose exec epub2audiobook /bin/bash

clean:
	docker-compose down -v --rmi all
	rm -rf data/uploads/* data/output/*

# Development commands
install:
	pip install -r requirements.txt -r requirements-web.txt

dev:
	FLASK_DEBUG=1 python -m flask --app web/app run --host=0.0.0.0 --port=5000

web:
	gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 600 web.app:app

# Quick start
quick-start: build run
	@echo "Quick start complete!"
