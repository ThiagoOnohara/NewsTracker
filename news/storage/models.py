from typing import Optional
from pydantic import BaseModel

class NewsItem(BaseModel):
    link: str  # usado como chave única
    title: str
    published: Optional[str] = None
    summary: Optional[str] = None
    topic: str
    is_new: bool = True  # (legado, pode ser removido em breve)
    status: Optional[str] = None  # "old", "new" ou "fresh"
    fetched_at: Optional[str] = None  # timestamp local da busca
