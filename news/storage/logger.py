import os
import json
from news.tracker.news_tracker import NewsTracker

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(STORAGE_DIR, exist_ok=True)

def export_all_news_to_json(tracker: NewsTracker):
    for topic, news_list in tracker.all_news.items():
        file_path = os.path.join(STORAGE_DIR, f"{topic}_history.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(news_list, f, ensure_ascii=False, indent=2)
