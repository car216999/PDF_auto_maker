"""임베딩 래퍼 — Ollama nomic-embed-text (768차원).

pipeline 은 Embedder 프로토콜에만 의존하므로, 테스트는 가짜 임베더를 주입하고
모델 교체(중장기: 다국어 임베딩)는 이 클래스만 바꾸면 된다.
4060 Ti 8GB 는 LLM 이 거의 차지하므로 임베딩은 CPU 로 도는 게 안전(소형 모델).
"""
from typing import Protocol

from app.config import settings


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OllamaEmbedder:
    def __init__(self, model: str | None = None, base_url: str | None = None):
        import ollama

        self.model = model or settings.embed_model
        self._client = ollama.Client(host=base_url or settings.ollama_base_url)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = self._client.embed(model=self.model, input=texts)
        return [list(v) for v in resp.embeddings]
