"""LLM 호출 래퍼 — Ollama 로컬 서빙.

generator 는 LLM 프로토콜에만 의존하므로, 테스트는 가짜 LLM 을 주입할 수 있고
서빙 백엔드(Ollama → 중장기 vLLM)는 이 클래스만 교체하면 된다.
"""
from typing import Protocol

from app.config import settings


class LLM(Protocol):
    def complete(self, prompt: str, json_mode: bool = True) -> str: ...


class OllamaClient:
    """로컬 Ollama 서버 호출 (외부 네트워크 0건)."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        import ollama

        self.model = model or settings.llm_model
        self._client = ollama.Client(host=base_url or settings.ollama_base_url)

    def complete(self, prompt: str, json_mode: bool = True) -> str:
        resp = self._client.generate(
            model=self.model,
            prompt=prompt,
            format="json" if json_mode else "",
            think=False,  # qwen3 추론 토큰 비활성화 — 양식 채움엔 불필요
            options={"temperature": 0.2},
        )
        return resp.response
