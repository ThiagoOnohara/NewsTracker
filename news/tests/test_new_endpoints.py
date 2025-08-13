# news/tests/test_news_endpoints.py
from datetime import datetime, timedelta, timezone

def _mk_item(title, link, published, region="US", source="UnitTest"):
    return {
        "title": title,
        "link": link,
        "published": published,
        "region": region,
        "source": source,
        "summary": "sum",
    }

def test_news_all_and_filters(client, monkeypatch):
    # Garante tópico vazio e sem fetch externo
    topic = "UnitTopic"
    r = client.post("/add-topic", params={"topic": topic, "region": "US"})
    assert r.status_code == 200

    # Injeta manualmente items no repositório
    from news.storage import repository as repo
    now = datetime.now(timezone.utc)
    fresh_dt = now.isoformat()
    old_dt = (now - timedelta(hours=8)).isoformat()
    new_dt = (now - timedelta(hours=2)).isoformat()

    news_list = [
        _mk_item("Fresh A", "http://x/f1", fresh_dt),
        _mk_item("New A", "http://x/n1", new_dt),
        _mk_item("Old A", "http://x/o1", old_dt),
    ]
    repo.add_news_batch(news_list, topic, int(now.timestamp()))

    # /news/{topic}/all
    r = client.get(f"/news/{topic}/all")
    assert r.status_code == 200
    data = r.json()["data"]
    titles = {d["title"] for d in data}
    assert {"Fresh A", "New A", "Old A"} <= titles

    # /news/{topic}/fresh
    r = client.get(f"/news/{topic}/fresh")
    fresh = {d["title"] for d in r.json()["data"]}
    assert "Fresh A" in fresh
    assert "New A" not in fresh
    assert "Old A" not in fresh

    # /news/{topic}/new
    r = client.get(f"/news/{topic}/new")
    new = {d["title"] for d in r.json()["data"]}
    assert "New A" in new
    assert "Fresh A" not in new
    assert "Old A" not in new

    # /news/{topic}/old
    r = client.get(f"/news/{topic}/old")
    old = {d["title"] for d in r.json()["data"]}
    assert "Old A" in old
    assert "Fresh A" not in old
    assert "New A" not in old

def test_mark_read_and_delete(client, monkeypatch):
    topic = "CRUDTopic"
    client.post("/add-topic", params={"topic": topic, "region": "US"})

    from news.storage import repository as repo
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    repo.add_news_batch([{
        "title": "T1", "link": "http://x/1", "published": now,
        "region": "US", "source": "Unit", "summary": ""
    }], topic, 0)

    # mark_read
    r = client.post("/news/read", params={"link": "http://x/1"})
    assert r.status_code == 200

    # delete
    r = client.delete("/news/delete", params={"link": "http://x/1"})
    assert r.status_code == 200

    # delete de novo -> 404
    r = client.delete("/news/delete", params={"link": "http://x/1"})
    assert r.status_code == 404
