import requests
from datetime import datetime, timezone
from typing import List, Dict
from .base import BaseFeed

class GdeltFeed(BaseFeed):
    BASE_URL = "https://api.gdeltproject.org/api/v1/search_ftxtsearch/search_ftxtsearch"
    TIMEOUT = 15

    REGION_LANG_MAP = {
        "US": "english",
        "BR": "portuguese",
        "DE": "german",
        "CN": "chinese",
        "JP": "japanese",
    }

    REGION_MAP = {
        "US": "unitedstates",
        "BR": "brazil",
        "DE": "germany",
        "CN": "china",
        "JP": "japan",
        "UK": "unitedkingdom",
        "GLOBAL": None
    }

    def __init__(self, query: str, max_items: int = 20, verify: bool = False, region: str = "GLOBAL"):
        self.query: str = query
        self.max_items: int = max_items
        self.verify: bool = verify
        self.region: str = region.upper()

    def fetch(self) -> List[Dict]:
        # Monta query: filtra por idioma se região específica
        lang = self.REGION_LANG_MAP.get(self.region, "")
        country = self.REGION_MAP.get(self.region, "")
        if lang:
            query_str = f"?{self.query}&sourcelang:{lang}&sourcecountry:{country}"
        else:
            query_str = self.query

        params = {
            "query": query_str,
            "output": "artlist",
            "dropdup": "true",
            "maxrecords": str(self.max_items),
        }
        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=self.TIMEOUT,
                verify=self.verify
            )
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"[ERROR] Fetch failed for '{self.query}': {e}")
            return []

        try:
            # Retorno é texto, cada linha = 1 artigo (TSV), sem cabeçalho
            lines = response.text.strip().split("\n")
        except Exception as e:
            print(f"[ERROR] Decode failed for '{self.query}': {e}")
            return []

        news = []
        cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0)
        print('GDELT found: {}'.format(lines))

        for line in lines[:self.max_items]:
            # Artlist: URL,Datetime,Title,Outlet
            # Exemplo: https://site.com 2024-08-06T08:02:02Z Some Title Jornal X
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue
            url, pubdate, title, source = parts[:4]
            
            published_dt = None
            if pubdate:
                try:
                    published_dt = datetime.strptime(pubdate, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                except Exception:
                    published_dt = None
            if published_dt and published_dt < cutoff_date:
                continue

            news.append({
                "title": title.strip(),
                "source": source.strip(),
                "link": url.strip(),
                "region": self.region,
                "published": published_dt.isoformat() if published_dt else None,
                "summary": None  # GDELT não retorna resumo
            })

        return news
