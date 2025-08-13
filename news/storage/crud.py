import os
import json
from typing import List, Dict
from threading import Lock
from datetime import datetime

from news.storage.models import NewsItem  # <--- USANDO MODELO CENTRALIZADO

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "news_db.json")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

db_lock = Lock()
