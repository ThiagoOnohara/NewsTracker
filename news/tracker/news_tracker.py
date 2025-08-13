from typing import Dict, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from news.feeds.base import BaseFeed
from news.feeds import GoogleNewsFeed, GdeltFeed
from datasketch import MinHash, MinHashLSH
import time

_MAX_ITEMS_PER_TOPIC = 500  # poda de memória para não crescer indefinidamente
_NUM_PERM = 128
_LSH_THRESHOLD = 0.8
_MAX_FETCH_WORKERS = 8      # paralelismo por tópico
_MAX_TOPIC_WORKERS = 4      # paralelismo entre tópicos

class NewsTracker:
    def __init__(self):
        # Cada tópico pode ter vários feeds
        self.feeds: Dict[str, List[BaseFeed]] = {}
        self.all_news: Dict[str, List[Dict]] = {}
        self.seen_links: Dict[str, Set[str]] = {}
        self.last_fetched: Dict[str, List[Dict]] = {}
        self.last_updated = None
        self.lsh_index: Dict[str, MinHashLSH] = {}
        self.minhashes: Dict[str, Dict[int, MinHash]] = {}
        self._next_id = 0
        self._lock = Lock()  # protege _next_id e estruturas por conta de threads

    def add_topic(self, topic: str, max_items=20, verify=False, region="US"):
        if topic in self.feeds:
            return
        google_feed = GoogleNewsFeed(topic, max_items, verify, region)
        # Se quiser reativar futuramente:
        # gdelt_feed = GdeltFeed(topic, max_items, verify, region)
        self.feeds[topic] = [google_feed]
        self.all_news[topic] = []
        self.seen_links[topic] = set()
        self.last_fetched[topic] = []
        self.lsh_index[topic] = MinHashLSH(threshold=_LSH_THRESHOLD, num_perm=_NUM_PERM)
        self.minhashes[topic] = {}

    def _build_minhash(self, text: str) -> MinHash:
        # Barato e estável: lower + split. Limita tokens para reduzir custo.
        m = MinHash(num_perm=_NUM_PERM)
        if text:
            for token in text.lower().split()[:64]:
                m.update(token.encode("utf-8"))
        return m

    def _prune_topic_memory(self, topic: str):
        # Poda para manter no máx. N itens por tópico (evita crescimento sem limite)
        lst = self.all_news.get(topic, [])
        if len(lst) > _MAX_ITEMS_PER_TOPIC:
            # mantém mais recentes (já ordenado por published desc no fluxo)
            self.all_news[topic] = lst[:_MAX_ITEMS_PER_TOPIC]

    def update_topic(self, topic: str, limit: int = 10) -> List[Dict]:
        feeds = self.feeds.get(topic, [])
        if not feeds:
            return []

        fresh: List[Dict] = []

        # Busca feeds em paralelo (melhor latência por tópico)
        with ThreadPoolExecutor(max_workers=min(len(feeds), _MAX_FETCH_WORKERS)) as ex:
            futures = [ex.submit(feed.fetch) for feed in feeds]
            for fut in as_completed(futures):
                try:
                    fetched = fut.result() or []
                except Exception as e:
                    print(f"[ERROR] Falha ao buscar feed {topic}: {e}")
                    continue

                for item in fetched:
                    link = item.get("link")
                    if not link:
                        continue
                    # dedupe simples por link
                    if link in self.seen_links[topic]:
                        continue

                    text = f"{item.get('title','')} {item.get('summary','')}".strip()
                    m = self._build_minhash(text)

                    # dedupe aproximado (título/summary parecidos)
                    if self.lsh_index[topic].query(m):
                        continue

                    # seção crítica (id + índices)
                    with self._lock:
                        self.lsh_index[topic].insert(self._next_id, m)
                        self.minhashes[topic][self._next_id] = m
                        item["_id"] = self._next_id
                        self._next_id += 1

                    self.seen_links[topic].add(link)
                    self.all_news[topic].append(item)
                    fresh.append(item)

        # Ordena por data de publicação (desc)
        self.all_news[topic].sort(key=lambda x: x.get("published") or "", reverse=True)
        fresh.sort(key=lambda x: x.get("published") or "", reverse=True)
        # Poda de memória
        self._prune_topic_memory(topic)

        self.last_fetched[topic] = fresh[:limit]
        return self.last_fetched[topic]

    def update_all(self):
        topics = list(self.feeds.keys())
        if not topics:
            self.last_updated = time.time()
            return

        # Atualiza vários tópicos em paralelo para diminuir o makespan total
        with ThreadPoolExecutor(max_workers=min(len(topics), _MAX_TOPIC_WORKERS)) as ex:
            futures = {ex.submit(self.update_topic, t): t for t in topics}
            for fut in as_completed(futures):
                t = futures[fut]
                try:
                    fut.result()
                except Exception as e:
                    print(f"[ERROR] update_topic falhou para '{t}': {e}")

        self.last_updated = time.time()

    def get_all_news(self, topic: str) -> List[Dict]:
        return self.all_news.get(topic, [])

    def get_last_news(self, topic: str) -> List[Dict]:
        return self.last_fetched.get(topic, [])
