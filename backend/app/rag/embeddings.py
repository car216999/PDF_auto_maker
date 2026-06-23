"""임베딩 래퍼 — Ollama BGE-M3 (1024차원, 다국어).

pipeline 은 Embedder 프로토콜에만 의존하므로, 테스트는 가짜 임베더를 주입하고
모델 교체는 이 클래스(또는 settings.embed_model)만 바꾸면 된다.
BGE-M3 는 한국어·영어 혼합 문서에 강해 견적서·기획서·선급 양식 검색에 적합.
(중장기: dense+sparse 하이브리드 — FlagEmbedding 으로 sparse 추가 + RRF)
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
