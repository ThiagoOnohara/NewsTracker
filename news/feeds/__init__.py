from .google import GoogleNewsFeed
from .gdelt import GdeltFeed

# Se quiser, exporte também a base:
from .base import BaseFeed

__all__ = ["GoogleNewsFeed", "GdeltFeed", "BaseFeed"]
