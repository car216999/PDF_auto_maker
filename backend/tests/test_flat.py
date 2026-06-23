"""평면(비-AcroForm) PDF 채우기 — 라벨 감지 + 좌표 오버레이 검증."""
import fitz

from app.injection.injector import PDFInjector
from app.parsing.parser import PDFParser
from app.schemas.generation import FilledField
from scripts.make_flat_quote import build


def test_flat_detection(tmp_path):
    """위젯 없는 평면 PDF에서 라벨+빈칸을 감지한다(제목은 제외)."""
    src = build(tmp_path / "flat.pdf")
    schema = PDFParser().parse(src, "f1")
    assert schema.metadata["is_flat"] is True
    labels = {f.label for f in schema.fields}
    assert {"회사명", "품목", "단가", "수량", "공급가액", "비고"} <= labels
    assert "견 적 서" not in labels  # 가운데 정렬 제목은 제외
    # 모든 필드에 빈칸 좌표가 있다
    for f in schema.fields:
        assert f.bbox is not None and f.bbox.x1 > f.bbox.x0


def test_flat_fill_overlays_values(tmp_path):
    """평면 PDF는 위젯이 없어도 스키마 좌표에 값이 오버레이된다."""
    src = build(tmp_path / "flat.pdf")
    schema = PDFParser().parse(src, "f1")
    by_label = {f.label: f.name for f in schema.fields}
    filled = [
        FilledField(name=by_label["회사명"], value="주식회사 엑시오"),
        FilledField(name=by_label["공급가액"], value="600만원"),
    ]
    out = PDFInjector(flatten=True).fill(src, filled, tmp_path / "out.pdf", schema=schema)
    doc = fitz.open(out)
    text = "".join(p.get_text() for p in doc)
    doc.close()
    assert "주식회사 엑시오" in text and "600만원" in text


def test_flat_section_detection(tmp_path):
    """섹션 제목(아래 빈 영역)과 인라인(밑줄) 모두 감지, 큰 글씨 제목은 제외."""
    from scripts.make_flat_plan import build as build_plan

    src = build_plan(tmp_path / "plan.pdf")
    schema = PDFParser().parse(src, "p1")
    by_label = {f.label: f for f in schema.fields}
    # 인라인 (밑줄 위, 한 줄)
    for lbl in ["프로젝트명", "팀명", "팀장"]:
        f = by_label[lbl]
        assert (f.bbox.y1 - f.bbox.y0) < 30  # 단일행
    # 섹션 (제목 아래 빈 영역, 문단)
    for lbl in ["추진배경 및 필요성", "서비스 내용", "주요 기술", "기대 효과"]:
        f = by_label[lbl]
        assert (f.bbox.y1 - f.bbox.y0) > 34  # 멀티라인 영역
    assert "프로젝트 기획서" not in by_label  # 큰 글씨 제목 제외


def test_table_cell_detection_and_fill(tmp_path):
    """표(셀 격자)에서 라벨 칸+값 칸을 짝지어 값 칸에 채운다."""
    from scripts.make_table_form import build as build_table

    src = build_table(tmp_path / "tbl.pdf")
    schema = PDFParser().parse(src, "t1")
    labels = {f.label for f in schema.fields}
    assert {"팀명", "팀원 및 역할", "주제 구분", "제안 배경 및 필요성"} <= labels

    by_label = {f.label: f.name for f in schema.fields}
    filled = [
        FilledField(name=by_label["팀명"], value="뚝딱 (TookTak)"),
        FilledField(name=by_label["제안 배경 및 필요성"], value="외부 API 의존을 제거한 온프레미스 RAG 시스템."),
    ]
    out = PDFInjector(flatten=True).fill(src, filled, tmp_path / "out.pdf", schema=schema)
    doc = fitz.open(out)
    text = "".join(p.get_text() for p in doc)
    doc.close()
    assert "뚝딱 (TookTak)" in text and "온프레미스" in text


def test_acroform_still_uses_widget_path(tmp_path):
    """AcroForm 양식은 is_flat=False — 기존 위젯 경로 유지."""
    from scripts.make_sample_form import build as build_form

    src = build_form(tmp_path / "q.pdf")
    schema = PDFParser().parse(src, "q1")
    assert schema.metadata["is_flat"] is False
    assert len(schema.fields) == 7  # 위젯 기반
