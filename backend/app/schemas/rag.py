"""RAG 검색 산출물 스키마 — 담당: 박은선 (청킹·임베딩·검색).

RAGPipeline.retrieve(query) 가 사내 문서에서 근거 청크를 찾아 반환한다.
생성 모듈은 '여기 담긴 근거 안에서만' 값을 만들어 환각을 제어한다.
"""
from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """검색된 근거 한 조각."""

    text: str
    source: str = Field(..., description="출처 문서/경로 — 환각·근거 일치율 측정에 사용")
    score: float = Field(0.0, description="유사도 점수 (높을수록 관련)")
    metadata: dict = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """단일 질의에 대한 top-k 결과."""

    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)
