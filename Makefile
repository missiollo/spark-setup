# spark-setup — skróty. `make help` wypisuje listę.
#
# Zestaw modeli wybiera SET (domyślnie c), np.: make models SET=a && make up SET=a

SET     ?= c
SHELL   := /bin/bash
HF_HOME_HOST ?= /data/hf
PY_IMAGE := python:3.12-slim

COMPOSE  = docker compose --env-file .run.env
PROFILES = $(shell grep -E '^COMPOSE_PROFILES=' .run.env 2>/dev/null | cut -d= -f2)

.PHONY: help bootstrap harden-ssh env models pin list up up-ui down restart logs ps test bench drop-caches

help: ## Lista poleceń
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
	@echo "  SET=$(SET)  (zestawy: $$(ls profiles | sed -E 's/set-(.*)\.env/\1/' | xargs))"

bootstrap: ## Przygotowanie hosta: pakiety, konto, grupy, /data (sudo)
	sudo ./bootstrap.sh $(USER)

harden-ssh: ## Wyłączenie logowania hasłem przez SSH (dopiero gdy klucz działa!)
	sudo ./bootstrap.sh --harden-ssh $(USER)

env: ## Złożenie .run.env dla zestawu SET
	@python3 scripts/render_env.py $(SET)

# Pobieranie w kontenerze: nic nie instalujemy przez pip na hoście.
# Uruchamiane z UID użytkownika i GID grupy llm, umask 002 -> pliki zapisywalne dla grupy.
define HF_RUN
	docker run --rm -t \
	  --user $$(id -u):$$(getent group llm | cut -d: -f3) \
	  -e HOME=/tmp -e HF_HOME=/data/hf -e HF_TOKEN \
	  -v $(HF_HOME_HOST):/data/hf -v $(CURDIR):/work:ro \
	  $(PY_IMAGE) sh -c "umask 002 && pip install -q --no-warn-script-location --user huggingface_hub pyyaml && python /work/scripts/download_models.py $(1)"
endef

models: ## Pobranie modeli zestawu SET do /data/hf
	@set -a; source .env; set +a; $(call HF_RUN,--set $(SET))

pin: ## Wypisanie SHA rewizji modeli zestawu SET (do wklejenia w models.yaml)
	@set -a; source .env; set +a; $(call HF_RUN,--set $(SET) --pin)

list: ## Lista modeli z manifestu
	@set -a; source .env; set +a; $(call HF_RUN,--list)

up: env ## Uruchomienie usług zestawu SET
	COMPOSE_PROFILES=$(PROFILES) $(COMPOSE) up -d
	@echo "Postęp ładowania: make logs   |   test: make test"

up-ui: env ## Jak up, plus Open WebUI na :8080
	COMPOSE_PROFILES=$(PROFILES),ui $(COMPOSE) up -d

down: ## Zatrzymanie wszystkich usług
	@test -f .run.env || python3 scripts/render_env.py $(SET)
	COMPOSE_PROFILES=embed,llm2,llm3,ui $(COMPOSE) down

restart: down up ## Restart (np. po zmianie profilu)

logs: ## Logi usług (Ctrl+C kończy podgląd)
	COMPOSE_PROFILES=embed,llm2,llm3,ui $(COMPOSE) logs -f --tail=100

ps: ## Stan kontenerów
	COMPOSE_PROFILES=embed,llm2,llm3,ui $(COMPOSE) ps

test: ## Szybki test API: lista modeli + krótka odpowiedź
	@curl -sf localhost:8000/v1/models | python3 -m json.tool
	@curl -sf localhost:8000/v1/chat/completions -H 'Content-Type: application/json' \
	  -d '{"model":"$(shell grep -E '^LLM_NAME=' .run.env | cut -d= -f2)","messages":[{"role":"user","content":"Odpowiedz jednym zdaniem: czym jest DGX Spark?"}],"max_tokens":200}' \
	  | python3 -c 'import json,sys; m=json.load(sys.stdin)["choices"][0]["message"]; print("\n>>", m.get("content"))'

bench: ## Pomiar TTFT i tok/s (wyniki w bench/results/)
	python3 bench/run_bench.py --base-url http://localhost:8000/v1 --out bench/results

drop-caches: ## Zwolnienie cache stron (zalecane przez NVIDIA przy OOM na starcie vLLM)
	sync && echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null
