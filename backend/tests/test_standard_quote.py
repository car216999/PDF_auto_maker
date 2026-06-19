"""표준 견적서(다필드·다열·표) 파싱 검증 — 라벨 추론 개선을 고정한다."""
import pytest

from app.parsing.parser import PDFParser
from scripts.make_standard_quote import build


@pytest.fixture(scope="module")
def schema(tmp_path_factory):
    pdf = build(tmp_path_factory.mktemp("f") / "standard_quote.pdf")
    return PDFParser().parse(pdf, "std")


def test_field_count(schema):
    assert len(schema.fields) == 27


def test_multicolumn_labels_not_merged(schema):
    """2열 레이아웃에서 우측 필드가 좌측 열 라벨을 끌어오지 않음."""
    labels = {f.name: f.label for f in schema.fields}
    assert labels["sup_reg_no"] == "등록번호"
    assert labels["sup_company"] == "상호"
    assert labels["sup_ceo"] == "대표자"
    assert labels["sup_addr"] == "주소"
    # 좌측 열도 정확
    assert labels["client_name"] == "수신"
    assert labels["quote_date"] == "견적일자"


def test_table_header_labels(schema):
    """표 셀 라벨은 컬럼 헤더(위)에서 추론."""
    labels = {f.name: f.label for f in schema.fields}
    for i in (1, 2, 3):
        assert labels[f"item{i}_name"] == "품명"
        assert labels[f"item{i}_qty"] == "수량"
        assert labels[f"item{i}_price"] == "단가"
        assert labels[f"item{i}_amount"] == "금액"


def test_totals_labels(schema):
    labels = {f.name: f.label for f in schema.fields}
    assert labels["total_supply"] == "공급가액"
    assert labels["total_tax"] == "부가세"
    assert labels["total_amount"] == "합계금액"
