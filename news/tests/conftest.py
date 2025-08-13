# news/tests/conftest.py
import json
import os
import types
import importlib
import tempfile
import contextlib
import pytest

@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    # Redireciona o DB para arquivo temporário vazio
    from news.storage import repository as repo
    db_file = tmp_path / "news_db.json"
    db_file.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(repo, "DB_PATH", str(db_file), raising=True)
    return str(db_file)

@pytest.fixture()
def app(monkeypatch, temp_db):
    # Patches para impedir network/scheduler no startup
    from news.api import main as api_main

    # 1) update_and_save_all: no-op
    monkeypatch.setattr(api_main, "update_and_save_all", lambda: {"status": "success"}, raising=True)

    # 2) scheduler.start/shutdown: no-op
    class DummyScheduler:
        def add_job(self, *a, **k): pass
        def start(self): pass
        def shutdown(self, wait=False): pass
    monkeypatch.setattr(api_main, "scheduler", DummyScheduler(), raising=True)

    # 3) classifier.classify_texts: retornos determinísticos p/ testes
    def fake_classify_texts(texts):
        return [
            {"sentiment": "Positivo", "probabilities": {
                "Muito Negativo": 0.01, "Negativo": 0.04, "Neutro": 0.1, "Positivo": 0.7, "Muito Positivo": 0.15
            }} for _ in texts
        ]
    monkeypatch.setattr(api_main.classifier, "classify_texts", fake_classify_texts, raising=True)

    return api_main.app

@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient
    # Usa contexto para garantir lifespan mas com patches aplicados
    with TestClient(app) as c:
        yield c
