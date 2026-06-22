"""주입 모듈 테스트 — 한글 렌더링·평탄화·체크박스·대화형 모드를 검증.

실제 PDF 를 생성·주입한 뒤 텍스트 추출로 결과를 확인한다(콘솔 인코딩 무관).
"""
import fitz

from app.injection.injector import PDFInjector
from app.schemas.generation import FilledField
from scripts.make_sample_form import build


def _korean_fields() -> list[FilledField]:
    return [
        FilledField(name="company_name", value="주식회사 엑시오"),
        FilledField(name="item", value="클라우드 서버 구축"),
        FilledField(name="supply_amount", value="600만원"),
        FilledField(name="vat_included", value="Y"),
    ]


def test_flatten_renders_korean(tmp_path):
    src = build(tmp_path / "q.pdf")
    out = PDFInjector(flatten=True).fill(src, _korean_fields(), tmp_path / "out.pdf")

    doc = fitz.open(out)
    text = "".join(p.get_text() for p in doc)
    widgets = sum(len(list(p.widgets() or [])) for p in doc)
    is_form = doc.is_form_pdf
    doc.close()

    assert "주식회사 엑시오" in text          # 한글 정상 렌더링
    assert "클라우드 서버 구축" in text
    assert "600만원" in text
    assert "X" in text                        # 체크박스 Y → X 표시
    assert widgets == 0                        # 평탄화 — 위젯 제거
    assert not is_form                          # 편집 불가 (폼 필드 0)


def test_unchecked_checkbox_has_no_mark(tmp_path):
    src = build(tmp_path / "q.pdf")
    out = PDFInjector(flatten=True).fill(
        src, [FilledField(name="vat_included", value="N")], tmp_path / "out.pdf"
    )
    doc = fitz.open(out)
    text = "".join(p.get_text() for p in doc)
    doc.close()
    assert "X" not in text  # N → 표시 없음


def test_interactive_mode_keeps_widgets_and_sets_values(tmp_path):
    src = build(tmp_path / "q.pdf")
    out = PDFInjector(flatten=False).fill(
        src,
        [FilledField(name="company_name", value="엑시오"),
         FilledField(name="item", value="서버 구축")],
        tmp_path / "out.pdf",
    )
    doc = fitz.open(out)
    vals = {w.field_name: w.field_value for p in doc for w in (p.widgets() or [])}
    is_form = doc.is_form_pdf
    doc.close()

    assert is_form                    # 위젯 유지 (대화형, 폼 필드 수 > 0)
    assert vals["company_name"] == "엑시오"
    assert vals["item"] == "서버 구축"


def test_long_value_shrinks_and_renders(tmp_path):
    """필드 폭을 넘는 긴 값도 글자 축소로 사라지지 않고 렌더링된다."""
    src = build(tmp_path / "q.pdf")
    long_val = "서울특별시 강남구 테헤란로 123 4층 견적담당부서"
    out = PDFInjector(flatten=True).fill(
        src, [FilledField(name="company_name", value=long_val)], tmp_path / "out.pdf"
    )
    doc = fitz.open(out)
    text = "".join(p.get_text() for p in doc)
    doc.close()
    assert "강남구" in text and "테헤란로" in text


def test_multiline_paragraph_wraps_and_renders(tmp_path):
    """긴 멀티라인 문단도 폰트 자동 축소로 박스에 들어가 렌더링된다.

    insert_textbox 는 오버플로우 시 아무것도 안 그리므로, 기본 폰트로는 넘치는
    긴 문단(아래 ~200자)이 '사라지지 않고' 축소되어 보이는지 검증한다.
    """
    from scripts.make_business_plan import build as build_bp

    src = build_bp(tmp_path / "bp.pdf")
    para = (
        "국내 749개 기업 조사 결과 절반 이상이 생성형 AI를 활용 중이며, 규제 산업에서는 "
        "온프레미스 LLM 도입이 확대되고 있다. 외부 API 의존을 제거하고 사내 데이터를 기반으로 한 "
        "RAG 시스템으로 데이터 주권을 확보하면서 정형 문서 작성 생산성을 높이는 것을 목표로 한다."
    )
    out = PDFInjector(flatten=True).fill(
        src, [FilledField(name="summary", value=para)], tmp_path / "out.pdf"
    )
    doc = fitz.open(out)
    text = "".join(p.get_text() for p in doc)
    doc.close()
    # 기본 폰트로는 넘치는 길이지만 축소되어 핵심 내용이 보존됨
    assert "온프레미스" in text and "데이터 주권" in text and "생산성" in text


def test_unknown_fields_ignored(tmp_path):
    src = build(tmp_path / "q.pdf")
    out = PDFInjector().fill(
        src, [FilledField(name="does_not_exist", value="x")], tmp_path / "out.pdf"
    )
    assert out.exists() and out.stat().st_size > 0
