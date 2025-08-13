
import os
import requests
from huggingface_hub import configure_http_backend
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import uuid
import json
from typing import List, Dict

# --- 1. Configurar cache customizado (opcional) ---
os.environ.setdefault("HF_HOME", os.path.expanduser("~/.cache/huggingface_hub"))

# --- 2. Configurar sessão HTTP para ignorar SSL (self-signed) ---
def backend_factory() -> requests.Session:
    session = requests.Session()
    session.verify = False
    return session

configure_http_backend(backend_factory=backend_factory)
# Explica: todas chamadas de download via Hugging Face Hub usarão esta sessão com verify=False :contentReference[oaicite:0]{index=0}

class NewsClassifier:
    """
    Classe para classificar sentimentos de textos/títulos de notícia.
    Usa modelo multilingue com saída em cinco categorias:
    Muito Negativo, Negativo, Neutro, Positivo, Muito Positivo.
    """

    def __init__(self, model_name: str = "tabularisai/multilingual-sentiment-analysis"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.labels = ["Muito Negativo", "Negativo", "Neutro", "Positivo", "Muito Positivo"]

    def classify_texts(self, texts: List[str]) -> List[Dict]:
        inputs = self.tokenizer(texts, return_tensors="pt", padding=True,
                                truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        results = []
        for text, prob in zip(texts, probs):
            scores = prob.tolist()
            idx = int(torch.argmax(prob).item())
            results.append({
                "id": str(uuid.uuid4()),
                "text": text,
                "sentiment": self.labels[idx],
                "probabilities": {lab: float(scores[i]) for i, lab in enumerate(self.labels)}
            })
        return results

if __name__ == "__main__":
    # Exemplo rápido de teste
    classifier = NewsClassifier()
    sample = ["The market is soaring with strong gains.",
              "A empresa enfrenta escândalo negativo grave."]
    res = classifier.classify_texts(sample)
    print(json.dumps(res, ensure_ascii=False, indent=2))