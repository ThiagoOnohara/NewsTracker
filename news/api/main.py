import time
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
from enum import Enum
from typing import Optional
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

from news.tracker.news_tracker import NewsTracker
from news.storage.repository import (
    add_news_batch,
    get_news_by_topic,
    mark_read,
    delete_news,
    get_all_news,
    update_news_sentiment,
)
from news.classifier.news_classifier import NewsClassifier
from news.summarizer.news_summarizer import NewsSummarizer
from news.notifier.news_notifier import Notifier


REFRESH_INTERVAL_MINUTES = 5          # intervalo de fetch de notícias (min)
CLASSIFY_INTERVAL_MINUTES = 15         # intervalo de classificação de sentimento (min)
EMAIL_SENDING_INTERVAL_MINUTES = 30     # janela de envio (minutes) usada no job de e-mail
EMAIL_SINCE_PUBLISHED_HOURS = 2  # janela de envio de e-mail (horas) para itens FRESH

THEME_REGION_DEFAULT = [
    # Main Themes
    ("Trump", "US"),
    ("Stocks", "GLOBAL"),
    ("FX", "GLOBAL"),
    ("Oil Markets", "GLOBAL"),
    ("Gold Price", "GLOBAL"),
    ("Fixed Income", "US"),
    # Wars
    ("Russia Ukraine", "GLOBAL"),
    ("Trade Deals and Tariffs", "GLOBAL"),
    ("Tariffs", "CN"),
    ("Tarifas", "BR"),
    # Local Themes
    ("Brasil Governo", "BR"),
    ("Brasil STF", "BR"),
    ("Lula", "BR"),
    ("Bolsonaro", "BR"),
    ("Congresso Câmara", "BR"),
    ("Senado", "BR"),
    # Geopolitical
    ("India", "US"),
    ("China", "US"),
    ("Russia", "US"),
    # Monetary Policy
    ("Federal Reserve", "US"),
    ("Central Banks", "US"),
]

# Carrega variáveis do .env
load_dotenv(override=True)

DEFAULT_TO = os.getenv("SEND_TO")                 # destinatário padrão de e-mail
DEFAULT_TEAMS_WEBHOOK = os.getenv("TEAMS_WEBHOOK_URL")  # webhook padrão (opcional)


class Region(str, Enum):
    us = "US"
    br = "BR"
    uk = "GB"
    cn = "CN"
    jn = "JN"
    de = "DE"


classifier = NewsClassifier()
summarizer = NewsSummarizer()
tracker = NewsTracker()

# Notifier com defaults do .env e usando o repositório de notícias
notifier = Notifier.from_env(get_all_news)

tracker.last_updated = int(time.time())
session_start_time = tracker.last_updated

# tópicos iniciais
for theme, region in THEME_REGION_DEFAULT:
    tracker.add_topic(theme, max_items=20, verify=False, region=region)

# Scheduler com configurações para evitar empilhamento de jobs
scheduler = BackgroundScheduler(
    job_defaults={
        "coalesce": True,         # junta execuções atrasadas
        "max_instances": 1,       # não roda dois iguais ao mesmo tempo
        "misfire_grace_time": 30, # 30s de tolerância
    }
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Agenda os jobs
    scheduler.add_job(update_and_save_all, "interval", minutes=REFRESH_INTERVAL_MINUTES, id="fetch_news")
    scheduler.add_job(classify_pending_news, "interval", minutes=CLASSIFY_INTERVAL_MINUTES, id="classify_sentiment")
    scheduler.add_job(lambda: send_fresh_email_job(window_hours=EMAIL_SINCE_PUBLISHED_HOURS), "interval", minutes=EMAIL_SENDING_INTERVAL_MINUTES, id=f"notify_outlook_{EMAIL_SENDING_INTERVAL_MINUTES}min")
    scheduler.start()

    # Primeira execução imediata para aquecer dados
    try:
        update_and_save_all()
    except Exception as e:
        print(f"[WARN] first update failed: {e}")

    yield
    scheduler.shutdown(wait=False)


def update_and_save_all():
    tracker.update_all()
    for topic in tracker.feeds:
        fresh = tracker.get_last_news(topic)
        if fresh:
            add_news_batch(fresh, topic, session_start_time)
    tracker.last_updated = int(time.time())
    print('[INFO] All news updated and saved.')
    return {"status": "success"}


def classify_pending_news():
    """
    Verifica no repositório se há notícias sem sentimento e executa classificação.
    """
    print("Checking and Updating News Classification")
    db_items = get_all_news()
    pending = [(item.link or item.title, item.title) for item in db_items if getattr(item, "sentiment", None) is None]

    total = len(pending)
    if total == 0:
        print("No pending items found.")
        return

    print(f"Found {total} pending items for classification.")
    keys, texts = zip(*pending)

    results = classifier.classify_texts(list(texts))
    for key, res in zip(keys, results):
        update_news_sentiment(key, res["sentiment"], res["probabilities"])

    print("Classification Finished!")


def send_fresh_email_job(window_hours: int):
    """
    Envia um e-mail com itens FRESH publicados na janela das últimas `window_hours`.
    Mantemos 2h de janela (DEFAULT) para não perder nada entre execuções horárias.
    """
    # Verifica destinatário padrão (do Notifier ou do .env)
    to = notifier.default_to or DEFAULT_TO
    if not to:
        print("[notify] SEND_TO não definido no .env — pulando envio.")
        return

    items = notifier.collect_fresh_news(hours=window_hours)
    if not items:
        print("[notify] Sem itens FRESH na janela — nada a enviar.")
        return

    subject = f"[NewsTracker] {len(items)} FRESH nas últimas {window_hours}h"
    html = notifier.render_email_html(items)
    try:
        notifier.send_via_outlook(to=to, subject=subject, html_body=html)
        print(f"[notify] Enviado para {to} ({len(items)} itens)")
    except Exception as e:
        print(f"[notify] Falha no envio via Outlook: {e}")

#%% APP

app = FastAPI(lifespan=lifespan)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajuste se precisar restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Compressão gzip para reduzir payloads de /news/* e /topics
app.add_middleware(GZipMiddleware, minimum_size=512)

@app.get("/health")
def health():
    return {"status": "ok", "ts": int(time.time())}

@app.get("/topics")
def get_topics():
    return {"status": "success", "data": list(tracker.feeds.keys())}

@app.get("/last-update")
def last_update():
    # (Opcional) cabeçalho de cache curto para aliviar o navegador
    resp = JSONResponse({"status": "success", "last_update": tracker.last_updated})
    resp.headers["Cache-Control"] = "public, max-age=5"
    return resp

@app.get("/news/{topic}/fresh")
def news_fresh(topic: str):
    if topic not in tracker.feeds:
        raise HTTPException(404, "Tópico não rastreado")
    items = get_news_by_topic(topic, status_filter="fresh")
    resp = {"status": "success", "data": [n.model_dump() for n in items]}
    return resp

@app.get("/news/{topic}/new")
def news_new(topic: str):
    if topic not in tracker.feeds:
        raise HTTPException(404, "Tópico não rastreado")
    items = get_news_by_topic(topic, status_filter="new")
    resp = {"status": "success", "data": [n.model_dump() for n in items]}
    return resp

@app.get("/news/{topic}/old")
def news_old(topic: str):
    if topic not in tracker.feeds:
        raise HTTPException(404, "Tópico não rastreado")
    items = get_news_by_topic(topic, status_filter="old")
    resp = {"status": "success", "data": [n.model_dump() for n in items]}
    return resp

@app.get("/news/{topic}/all")
def news_all(topic: str):
    if topic not in tracker.feeds:
        raise HTTPException(404, "Tópico não rastreado")
    items = get_news_by_topic(topic)
    resp = {"status": "success", "data": [n.model_dump() for n in items]}
    return resp

# POST
@app.post("/force-update")
def force_update():
    return update_and_save_all()

@app.post("/news/read")
def api_mark_read(link: str):
    if not mark_read(link):
        raise HTTPException(404, "Link não encontrado")
    return {"status": "success"}

@app.post("/add-topic")
def add_topic(topic: str, region: Region = Region.us):
    """
    Adiciona um novo tópico ao tracker.
    """
    if topic in tracker.feeds:
        return {"status": "exists", "region": region.value}
    tracker.add_topic(topic, max_items=20, verify=False, region=region.value)
    return {"status": "success", "region": region.value}

@app.post("/notify/outlook")
def notify_outlook(hours: int = 2, to: Optional[str] = None):
    r = notifier.notify_outlook(hours=hours, to=to)
    if r.get("status") == "error":
        raise HTTPException(400, r["error"])
    return r

@app.post("/notify/teams")
def notify_teams(hours: int = 2, webhook_url: Optional[str] = None):
    r = notifier.notify_teams(hours=hours, webhook_url=webhook_url)
    if r.get("status") == "error":
        raise HTTPException(400, r["error"])
    return r

# DELETE
@app.delete("/news/delete")
def api_delete_news(link: str):
    if not delete_news(link):
        raise HTTPException(404, "Link não encontrado")
    return {"status": "success"}

@app.delete("/remove-topic")
def remove_topic(topic: str):
    if topic not in tracker.feeds:
        raise HTTPException(404, "Tópico não encontrado")
    # limpeza defensiva
    del tracker.feeds[topic]
    del tracker.all_news[topic]
    del tracker.seen_links[topic]
    del tracker.last_fetched[topic]
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("news.api.main:app", host="0.0.0.0", port=8000, reload=True)
