from abc import ABC, abstractmethod
from typing import List, Dict

class BaseFeed(ABC):
    @abstractmethod
    def fetch(self) -> List[Dict]:
        pass
