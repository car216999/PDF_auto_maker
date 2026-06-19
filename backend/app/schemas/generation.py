"""LLM 생성 산출물 스키마 — 담당: 이권형 (LLM 서빙·생성).

FieldGenerator 가 필드별로 RAG 근거를 참조해 채울 값을 만든다.
grounded/evidence 는 기획서 KPI '환각·근거 일치율 ≥ 90%' 측정의 근거가 된다.
"""
from pydantic import BaseModel, Field


class FilledField(BaseModel):
    """한 필드에 대해 생성된 값."""

    name: str = Field(..., description="FormField.name 과 1:1 대응")
    value: str = Field("", description="채울 값")
    grounded: bool = Field(False, description="RAG 근거에 실제로 존재하는 값인가")
    evidence: list[str] = Field(default_factory=list, description="근거가 된 출처들")
    confidence: float = 0.0


class GenerationResult(BaseModel):
    """양식 전체에 대한 생성 결과. 미리보기 단계에 표시."""

    form_id: str
    fields: list[FilledField] = Field(default_factory=list)
    model: str = ""

    @property
    def grounded_ratio(self) -> float:
        """근거 일치율 (KPI 측정용). 빈 필드는 제외하고 '채운 값' 기준으로 계산.

        의도적으로 비운 칸(해당 없음)이 근거율을 깎지 않도록 한다.
        """
        filled = [f for f in self.fields if f.value.strip()]
        if not filled:
            return 0.0
        return sum(f.grounded for f in filled) / len(filled)
