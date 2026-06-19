"""양식 저장소 (MVP: 인메모리). form_id 로 파싱 결과·원본 경로를 보관.

중장기: 메타 DB 로 교체 (이 인터페이스 유지).
"""
from dataclasses import dataclass
from pathlib import Path

from app.schemas.form import FormSchema


@dataclass
class FormRecord:
    form_id: str
    src_path: Path
    schema: FormSchema


class FormStore:
    def __init__(self) -> None:
        self._records: dict[str, FormRecord] = {}

    def put(self, record: FormRecord) -> None:
        self._records[record.form_id] = record

    def get(self, form_id: str) -> FormRecord | None:
        return self._records.get(form_id)


store = FormStore()
