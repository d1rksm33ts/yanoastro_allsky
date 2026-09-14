SHELL := /bin/sh

.PHONY: validate build up down status logs backup

validate:
	./scripts/validate.sh

build: validate
	docker compose build

up: validate
	docker compose up -d

down:
	docker compose down

status:
	docker compose ps

logs:
	docker compose logs --tail=200

backup:
	docker compose --profile operations run --rm backup
