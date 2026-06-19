"""파서 단위 테스트 — 샘플 견적서 AcroForm 에서 필드·라벨·타입·메타를 정확히 뽑는지.

콘솔 인코딩에 의존하지 않고 한글 라벨까지 정확히 검증한다.
"""
from pathlib import Path

import pytest

from app.parsing.parser import PDFParser
from app.schemas.form import FieldType
from scripts.make_sample_form import build

ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module")
def sample_pdf(tmp_path_factory) -> Path:
    """매번 새로 생성한 샘플 양식 (외부 파일에 의존하지 않음)."""
    out = tmp_path_factory.mktemp("forms") / "sample_quote.pdf"
    return build(out)


@pytest.fixture(scope="module")
def schema(sample_pdf):
    return PDFParser().parse(sample_pdf, form_id="t1")


def test_metadata(schema):
    assert schema.page_count == 1
    assert schema.metadata["is_form"] is True
    assert len(schema.fields) == 7


def test_field_names(schema):
    names = {f.name for f in schema.fields}
    assert names == {
        "company_name", "item", "unit_price",
        "quantity", "supply_amount", "note", "vat_included",
    }


def test_korean_labels(schema):
    labels = {f.name: f.label for f in schema.fields}
    assert labels["company_name"] == "회사명"
    assert labels["item"] == "품목"
    assert labels["unit_price"] == "단가"
    assert labels["quantity"] == "수량"
    assert labels["supply_amount"] == "공급가액"
    assert labels["note"] == "비고"
    assert labels["vat_included"] == "부가세 포함"  # 다중 단어 라벨 결합


def test_types_and_constraints(schema):
    by_name = {f.name: f for f in schema.fields}
    # 텍스트 6 + 체크박스 1
    assert by_name["company_name"].field_type == FieldType.TEXT
    assert by_name["vat_included"].field_type == FieldType.CHECKBOX
    # maxlen 은 quantity 만 설정(5)
    assert by_name["quantity"].max_length == 5
    assert by_name["company_name"].max_length is None


def test_coordinates_present(schema):
    for f in schema.fields:
        assert f.bbox is not None
        assert f.bbox.x1 > f.bbox.x0
        assert f.bbox.y1 > f.bbox.y0


def test_flat_pdf_returns_empty(tmp_path):
    """위젯 없는 평면 PDF 는 빈 fields + is_form=False (중장기 항목, 안전 처리)."""
    import fitz

    flat = tmp_path / "flat.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(flat)
    doc.close()

    s = PDFParser().parse(flat, form_id="flat1")
    assert s.fields == []
    assert s.metadata["is_form"] is False
