# news/tests/test_classification_job.py
def test_classify_pending_news_updates_sentiment(client):
    # Usa o classifier já “falso” do conftest (Positivo)
    topic = "ClassifyTopic"
    client.post("/add-topic", params={"topic": topic, "region": "US"})

    from news.storage import repository as repo
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    repo.add_news_batch([
        {"title": "S/ sentiment 1", "link": "http://x/c1", "published": now, "region": "US", "source": "U", "summary": ""},
        {"title": "S/ sentiment 2", "link": "http://x/c2", "published": now, "region": "US", "source": "U", "summary": ""},
    ], topic, 0)

    # Executa o job diretamente
    from news.api import main as api_main
    api_main.classify_pending_news()

    # Verifica que ficou com "Positivo"
    items = repo.get_news_by_topic(topic)
    sentiments = {i.sentiment for i in items}
    assert "Positivo" in sentiments
    assert None not in sentiments
