# news/tests/test_api_basic.py
import time
import json

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "ok"
    assert isinstance(j["ts"], int)

def test_topics_add_remove(client):
    # Deve ter os tópicos default
    r = client.get("/topics")
    assert r.status_code == 200
    topics = set(r.json()["data"])
    assert len(topics) >= 1  # default carregado no módulo

    # Adiciona novo
    r = client.post("/add-topic", params={"topic": "TestTopic", "region": "US"})
    assert r.status_code == 200
    r = client.get("/topics")
    assert "TestTopic" in set(r.json()["data"])

    # Remove
    r = client.delete("/remove-topic", params={"topic": "TestTopic"})
    assert r.status_code == 200
    r = client.get("/topics")
    assert "TestTopic" not in set(r.json()["data"])

def test_last_update(client):
    r = client.get("/last-update")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "success"
    assert isinstance(j["last_update"], int)
