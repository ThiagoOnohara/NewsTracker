import time
import requests
import feedparser
from datetime import datetime, timezone
from typing import List, Dict
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from .base import BaseFeed

# ---------- HTTP session global com pool + retry (menor latência / resiliente) ----------
_SESSION = requests.Session()
_RETRY = Retry(
    total=3,
    backoff_factor=0.3,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset({"GET"}),
    raise_on_status=False,
)
_ADAPTER = HTTPAdapter(pool_connections=20, pool_maxsize=50, max_retries=_RETRY)
_SESSION.mount("https://", _ADAPTER)
_SESSION.headers.update({"User-Agent": "NewsTracker/1.0 (+https://localhost)"})

# ---------- Cache em memória com TTL curto (evita hits repetidos no intervalo) ----------
_CACHE: Dict[str, Dict] = {}  # key -> {"expires": float_ts, "data": List[Dict]}
_CACHE_TTL_SEC = 60  # suficiente dado seu REFRESH_INTERVAL em minutos

class GoogleNewsFeed(BaseFeed):
    BASE_URL = "https://news.google.com/rss/search"
    TIMEOUT = 10
    REGION_CONFIG = {
        "BR": {"hl": "pt-BR", "ceid": "BR:pt"},
        "US": {"hl": "en-US", "ceid": "US:en"},
        "GB": {"hl": "en-GB", "ceid": "GB:en"},
    }

    def __init__(self, query: str, max_items: int = 20, verify: bool = False, region: str = "US"):
        self.query: str = query
        self.max_items: int = max_items
        self.verify: bool = verify
        self.region: str = region.upper()
        config = self.REGION_CONFIG.get(self.region, {"hl": "en-US", "ceid": "US:en"})
        self.hl = config["hl"]
        self.ceid = config["ceid"]

    def _cache_key(self) -> str:
        return f"gnews::{self.query}::{self.hl}::{self.region}::{self.ceid}::{self.max_items}"

    def fetch(self) -> List[Dict]:
        now = time.time()
        ckey = self._cache_key()
        cached = _CACHE.get(ckey)
        if cached and cached["expires"] > now:
            # retorno defensivo (cópia rasa) para evitar mutações externas
            return list(cached["data"])

        params = {
            "q": self.query,
            "hl": self.hl,
            "gl": self.region,
            "ceid": self.ceid,
        }

        try:
            # usa sessão global com pool + retry
            response = _SESSION.get(
                self.BASE_URL,
                params=params,
                timeout=self.TIMEOUT,
                verify=self.verify,  # mantém compatibilidade do parâmetro
            )
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"[ERROR] Fetch failed for '{self.query}': {e}")
            return []

        feed = feedparser.parse(response.text)
        # Only today (mantém sua lógica original)
        cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        news: List[Dict] = []
        # processa mais de max_items para permitir filtragem por data e ainda devolver até max_items
        for entry in feed.entries:
            # published_parsed preferencial; fallback para updated_parsed
            published_dt = None
            try:
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published_dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            except Exception:
                published_dt = None

            if published_dt and published_dt < cutoff_date:
                continue

            raw_title = entry.get("title") or ""
            # Google costuma usar "Título - Fonte"; usa rsplit para evitar cortar títulos que têm '-'
            source = ""
            title_only = raw_title
            if " - " in raw_title:
                # Ex.: "Apple sobe no pré-mercado - Reuters"
                title_only, source = raw_title.rsplit(" - ", 1)
            elif "-" in raw_title:
                # fallback menos preciso
                parts = raw_title.split("-")
                if len(parts) >= 2:
                    title_only = " ".join(parts[:-1]).strip()
                    source = parts[-1].strip()

            item = {
                "title": (title_only or "").strip(),
                "source": (source or "").strip(),
                "link": entry.get("link"),
                "region": entry.get("region", self.region),
                "published": published_dt.isoformat() if published_dt else None,
                "summary": entry.get("summary"),
            }
            news.append(item)

            if len(news) >= self.max_items:
                break

        # salva em cache com TTL
        _CACHE[ckey] = {"expires": now + _CACHE_TTL_SEC, "data": news}
        return news
