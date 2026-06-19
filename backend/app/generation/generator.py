"""LLM 생성 — 담당: 이권형.

각 빈 필드에 대해 RAG 근거를 프롬프트에 주입하고 '근거 안에서만' 값을 생성한다.
양식 전체를 단일 호출로 채워 필드 간 계산(공급가액 = 단가×수량)도 한 맥락에서 처리.
생성 후 grounded(근거 내 존재) 여부를 표시해 KPI '근거 일치율' 측정의 근거로 쓴다.
"""
import re

from app.config import settings
from app.generation.llm import LLM, OllamaClient
from app.generation.prompts import build_prompt, parse_json_values
from app.rag.pipeline import RAGPipeline
from app.schemas.form import FormSchema
from app.schemas.generation import FilledField, GenerationResult


def _is_grounded(value: str, evidence: str) -> bool:
    """값이 근거에 실제로 존재하는가 (느슨한 휴리스틱 — KPI 측정의 1차 신호).

    완전 일치 또는 2글자 이상 토큰의 부분 일치. 계산값(600만원 등)은 근거에
    원문이 없을 수 있어 false 가 날 수 있으며, 정밀 측정은 별도 평가에서 수행한다.
    """
    v = value.strip()
    if not v or not evidence:
        return False
    if v in evidence:
        return True
    tokens = [t for t in re.split(r"[\s,/()]+", v) if len(t) >= 2]
    return any(t in evidence for t in tokens)


class FieldGenerator:
    def __init__(self, rag: RAGPipeline, llm: LLM | None = None):
        self.rag = rag
        self._llm = llm  # None 이면 첫 사용 시 실제 Ollama 로 지연 생성

    @property
    def llm(self) -> LLM:
        if self._llm is None:
            self._llm = OllamaClient()
        return self._llm

    def generate(
        self, form: FormSchema, concept: str, overrides: dict[str, str] | None = None
    ) -> GenerationResult:
        overrides = overrides or {}

        # ① RAG 근거 수집 (컨셉 + 전체 라벨로 1회 검색)
        labels = " ".join(f.label or f.name for f in form.fields)
        retrieval = self.rag.retrieve(f"{concept} {labels}".strip(), settings.top_k)
        evidence = "\n".join(c.text for c in retrieval.chunks)
        sources = [c.source for c in retrieval.chunks]

        # ② override 되지 않은 필드만 LLM 으로 채움
        todo = [f for f in form.fields if f.name not in overrides]
        values: dict[str, str] = {}
        if todo:
            raw = self.llm.complete(build_prompt(concept, todo, evidence), json_mode=True)
            values = parse_json_values(raw)

        # ③ FilledField 조립
        filled: list[FilledField] = []
        for f in form.fields:
            if f.name in overrides:
                filled.append(FilledField(name=f.name, value=overrides[f.name],
                                          grounded=True, confidence=1.0))
                continue
            val = values.get(f.name, "").strip()
            # 근거 = 사내 문서 또는 사용자 컨셉에 존재 (사용자 입력은 환각이 아님)
            in_evidence = _is_grounded(val, evidence)
            grounded = in_evidence or _is_grounded(val, concept)
            filled.append(FilledField(
                name=f.name,
                value=val,
                grounded=grounded,
                evidence=sources if in_evidence else [],
                confidence=0.7 if val else 0.0,
            ))

        return GenerationResult(form_id=form.form_id, fields=filled, model=settings.llm_model)
