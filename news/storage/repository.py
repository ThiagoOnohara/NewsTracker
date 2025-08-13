import os, json
from threading import Lock
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "news_db.json")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
db_lock = Lock()

class NewsItem(BaseModel):
    link: str
    title: str
    source: str
    published: Optional[str] = None
    region: Optional[str] = None
    summary: Optional[str] = None
    topic: str
    status: Optional[str] = None  # 'old', 'new', 'fresh'
    fetched_at: Optional[str] = None
    sentiment: Optional[str] = None
    probabilities: Optional[dict] = None

def normalize(text: str) -> str:
    return ''.join(e.lower() for e in text if e.isalnum() or e.isspace()).strip()

def load_db() -> Dict[str, NewsItem]:
    if not os.path.exists(DB_PATH):
        return {}
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return {normalize(item["title"]): NewsItem(**item) for item in raw}
    except (json.JSONDecodeError, ValueError):
        print("[WARN] news_db.json está vazio ou corrompido. Recriando do zero.")
        return {}

def save_db(db: Dict[str, NewsItem]):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump([n.model_dump() for n in db.values()], f, ensure_ascii=False, indent=2)

def classify_news_status(publ: Optional[str], now: datetime) -> str:
    if not publ:
        return "old"
    try:
        pub_dt = datetime.fromisoformat(publ)
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
    except Exception:
        return "old"
    delta = now - pub_dt
    if delta <= timedelta(minutes=30):
        return "fresh"
    elif delta <= timedelta(hours=6):  # <= 6h é NEW, >6h é OLD
        return "new"
    else:
        return "old"

def add_news_batch(news_list: List[Dict], topic: str, start_ts: int):
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    with db_lock:
        db = load_db()
        seen_titles = set(db.keys())
        for item in news_list:
            title = item.get("title")
            link = item.get("link")
            if not title or not link:
                continue
            publ = item.get("published")
            region = item.get('region')
            # Busca a região do tópico se não houver na notícia
            if not region:
                region = "GLOBAL"
            norm_title = normalize(title.strip())
            #print('REGION:', region)


            # Classificação por tempo (status)
            status = classify_news_status(publ, now_dt)
            if norm_title not in seen_titles:
                db[norm_title] = NewsItem(
                    **item,
                    topic=topic,
                    status=status,
                    fetched_at=now_iso,
                    sentiment=None,
                    probabilities=None,
                )
                seen_titles.add(norm_title)
        save_db(db)

def get_news_by_topic(topic: str, status_filter: Optional[str] = None):
    with db_lock:
        db = load_db()
        all_items = [n for n in db.values() if n.topic == topic]
        now_dt = datetime.now(timezone.utc)
        updated = False
        for n in all_items:
            new_status = classify_news_status(n.published, now_dt)
            if n.status != new_status:
                n.status = new_status
                updated = True
        if updated:
            # Atualiza apenas o status no banco, sem perder outras notícias
            for n in all_items:
                norm = normalize(n.title)
                db[norm] = n
            save_db(db)
        if status_filter:
            all_items = [n for n in all_items if n.status == status_filter]
        return sorted(all_items, key=lambda n: n.published or "", reverse=True)
    
def mark_read(link: str) -> bool:
    with db_lock:
        db = load_db()
        for key, item in db.items():
            if item.link == link:
                save_db(db)
                return True
    return False

def delete_news(link: str) -> bool:
    with db_lock:
        db = load_db()
        for key in list(db.keys()):
            if db[key].link == link:
                del db[key]
                save_db(db)
                return True
    return False

def get_all_news() -> List[NewsItem]:
    with db_lock:
        return list(load_db().values())

def update_news_sentiment(link_or_title: str, sentiment: str, probabilities: dict) -> bool:
    with db_lock:
        db = load_db()
        norm = normalize(link_or_title)
        if norm in db:
            item = db[norm]
        else:
            item = next((n for n in db.values() if n.link == link_or_title), None)
        if not item:
            return False
        item.sentiment = sentiment
        item.probabilities = probabilities
        save_db(db)
        return True
