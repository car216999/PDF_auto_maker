"""End-to-End 오케스트레이션: 파싱 → RAG → 생성 → 주입.

기획서 6장 처리 흐름을 모듈 의존성 단방향(DAG)으로 연결한다.
각 모듈이 스텁이어도 이 경로는 처음부터 끝까지 동작한다 (최소 동작 산출물).
실제 구현이 들어오면 각 모듈만 교체하면 되고, 이 오케스트레이터는 그대로다.
"""
import uuid
from pathlib import Path

from app.config import settings
from app.generation.generator import FieldGenerator
from app.injection.injector import PDFInjector
from app.parsing.parser import PDFParser
from app.rag.pipeline import RAGPipeline
from app.schemas.form import FormSchema
from app.schemas.generation import FilledField, GenerationResult
from app.services.store import FormRecord, store


class Orchestrator:
    def __init__(self) -> None:
        self.parser = PDFParser()
        self.rag = RAGPipeline()
        self.generator = FieldGenerator(self.rag)
        self.injector = PDFInjector()

    def upload(self, pdf_path: Path) -> FormSchema:
        """① 양식 업로드 → 파싱 → 저장."""
        form_id = uuid.uuid4().hex[:12]
        schema = self.parser.parse(pdf_path, form_id)
        store.put(FormRecord(form_id=form_id, src_path=pdf_path, schema=schema))
        return schema

    def generate(
        self, form_id: str, concept: str, overrides: dict[str, str] | None = None
    ) -> GenerationResult:
        """② 컨셉 → RAG 근거 → LLM 생성."""
        record = store.get(form_id)
        if record is None:
            raise KeyError(form_id)
        return self.generator.generate(record.schema, concept, overrides)

    def fill(self, form_id: str, fields: list[FilledField]) -> Path:
        """③ 확정값 → PDF 주입."""
        record = store.get(form_id)
        if record is None:
            raise KeyError(form_id)
        out = settings.output_dir / f"{form_id}_filled.pdf"
        return self.injector.fill(record.src_path, fields, out)


orchestrator = Orchestrator()
