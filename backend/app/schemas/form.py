"""PDF 파싱 산출물 스키마 — 담당: 채요한 (PDF 파싱·폼필드 추출).

PDFParser 가 빈 양식을 읽어 이 스키마로 정형화한다.
이 모델은 RAG·생성·주입 전 모듈이 공유하는 '양식의 단일 진실 공급원'이다.
"""
from enum import Enum

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    TEXT = "text"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    CHOICE = "choice"  # 드롭다운/콤보
    SIGNATURE = "signature"
    UNKNOWN = "unknown"


class BBox(BaseModel):
    """필드 위젯의 좌표 (PyMuPDF 좌표계: 좌상단 원점, y 아래로 증가, 단위 pt).

    좌표 정밀 주입의 근거. 주입(injection) 모듈도 동일 좌표계를 사용한다.
    """

    x0: float
    y0: float
    x1: float
    y1: float


class FormField(BaseModel):
    """빈 양식의 단일 입력 필드."""

    name: str = Field(..., description="AcroForm 필드명 (주입 시 키)")
    label: str = Field("", description="사람이 읽는 라벨 (예: '공급가액'). LLM 채움의 단서")
    field_type: FieldType = FieldType.TEXT
    page: int = Field(0, description="0-base 페이지 인덱스")
    bbox: BBox | None = None
    required: bool = False
    options: list[str] = Field(default_factory=list, description="choice/radio 선택지")
    max_length: int | None = None


class FormSchema(BaseModel):
    """파싱된 양식 전체. POST /forms/upload 의 응답 본체."""

    form_id: str
    filename: str
    page_count: int
    fields: list[FormField] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict, description="제목·작성자 등 PDF 메타")
