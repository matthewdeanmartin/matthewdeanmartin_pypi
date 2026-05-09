.PHONY: sync serve serve-prod check

HOST ?= 127.0.0.1
PORT ?= 8010

sync:
	uv sync

serve: sync
	uv run uvicorn app:app --reload --host $(HOST) --port $(PORT)

serve-prod: sync
	uv run uvicorn app:app --host $(HOST) --port $(PORT)

check: sync
	uv run python demo_check.py
