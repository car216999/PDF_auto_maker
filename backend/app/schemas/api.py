"""웹 API 요청/응답 스키마 — 담당: 김세경 (프론트엔드·통합).

프론트엔드(React) 와 백엔드(FastAPI) 사이의 계약.
UI 흐름: 업로드 → 컨셉 입력 → 생성 → 미리보기 → 다운로드.
"""
from pydantic import BaseModel, Field

from app.schemas.form import FormSchema
from app.schemas.generation import FilledField, GenerationResult


class UploadResponse(BaseModel):
    """빈 양식 업로드 결과 — 추출된 필드 스키마를 그대로 돌려준다."""

    form: FormSchema


class GenerateRequest(BaseModel):
    """컨셉 입력 → 생성 요청."""

    concept: str = Field(..., description="문서 컨셉/지시 (예: '엑시오 클라우드 구축 견적')")
    overrides: dict[str, str] = Field(
        default_factory=dict, description="사용자가 직접 지정한 필드값 (name -> value)"
    )


class GenerateResponse(BaseModel):
    result: GenerationResult


class FillRequest(BaseModel):
    """미리보기에서 확정한 값으로 PDF 주입 요청."""

    fields: list[FilledField]


class DownloadResponse(BaseModel):
    """채워진 PDF 의 다운로드 식별자."""

    form_id: str
    download_path: str
