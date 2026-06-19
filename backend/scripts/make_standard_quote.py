"""표준 견적서 AcroForm 생성기 — 실무용 다필드 양식.

구성: 문서정보(일자·번호·유효기간) + 수신 + 공급자(등록번호·상호·대표자·주소·업태·종목·연락처)
      + 품목 명세표(3행: 품명·수량·단가·금액) + 합계(공급가액·부가세·합계금액) + 비고.
좌측 라벨 필드는 라벨이 왼쪽에, 표 셀은 컬럼 헤더가 위에 있어 파서가 라벨을 추론한다.

사용:  uv run python -m scripts.make_standard_quote
결과:  data/forms/standard_quote.pdf
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

KFONT = "HYSMyeongJo-Medium"
pdfmetrics.registerFont(UnicodeCIDFont(KFONT))

W, H = A4


def build(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4)
    form = c.acroForm

    def label(x, y, text, size=10):
        c.setFont(KFONT, size)
        c.drawString(x, y, text)

    def header(x, y, text, size=10):
        c.setFont(KFONT, size)
        c.drawCentredString(x, y, text)

    def field(name, x, y, w, h=20, tip=""):
        form.textfield(name=name, tooltip=tip or name, x=x, y=y, width=w, height=h,
                       borderStyle="underlined", borderWidth=1, forceBorder=True,
                       fontName="Helvetica", fontSize=10)

    # 제목
    c.setFont(KFONT, 24)
    c.drawCentredString(W / 2, H - 70, "견 적 서")

    # --- 좌측: 수신 + 문서정보 ---
    lx, lfx, lw = 70, 130, 150
    rows_left = [
        ("수신", "client_name", H - 130),
        ("견적일자", "quote_date", H - 160),
        ("견적번호", "quote_no", H - 190),
        ("유효기간", "valid_until", H - 220),
    ]
    for lab, name, y in rows_left:
        label(lx, y + 4, lab)
        field(name, lfx, y, lw, tip=lab)

    # --- 우측: 공급자 ---
    c.setFont(KFONT, 11)
    c.drawString(320, H - 92, "[ 공급자 ]")
    rx, rfx, rw = 320, 390, 165
    rows_right = [
        ("등록번호", "sup_reg_no", H - 130),
        ("상호", "sup_company", H - 160),
        ("대표자", "sup_ceo", H - 190),
        ("주소", "sup_addr", H - 220),
        ("업태", "sup_biz_type", H - 250),
        ("종목", "sup_biz_item", H - 280),
        ("연락처", "sup_tel", H - 310),
    ]
    for lab, name, y in rows_right:
        label(rx, y + 4, lab)
        field(name, rfx, y, rw, tip=lab)

    # --- 품목 명세표 ---
    table_top = H - 350
    cols = [
        ("품명", "name", 70, 200),
        ("수량", "qty", 280, 60),
        ("단가", "price", 350, 100),
        ("금액", "amount", 460, 110),
    ]
    # 헤더
    c.setLineWidth(0.8)
    c.line(70, table_top, 570, table_top)
    for title, _, cx, cw in cols:
        header(cx + cw / 2, table_top - 15, title)
    c.line(70, table_top - 22, 570, table_top - 22)
    # 행 3개
    for i in range(1, 4):
        ry = table_top - 22 - i * 26
        for _, key, cx, cw in cols:
            field(f"item{i}_{key}", cx, ry, cw, h=22, tip=f"{i}행 {key}")
    c.line(70, table_top - 22 - 3 * 26, 570, table_top - 22 - 3 * 26)

    # --- 합계 (우측 정렬) ---
    ty = table_top - 22 - 3 * 26 - 30
    tx, tfx, tw = 350, 440, 130
    totals = [
        ("공급가액", "total_supply", ty),
        ("부가세", "total_tax", ty - 28),
        ("합계금액", "total_amount", ty - 56),
    ]
    for lab, name, y in totals:
        label(tx, y + 4, lab)
        field(name, tfx, y, tw, tip=lab)

    # --- 비고 ---
    ny = ty - 100
    label(70, ny + 24, "비고")
    field("note", 130, ny, 440, h=40, tip="비고")

    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent
    out = build(root / "data" / "forms" / "standard_quote.pdf")
    print(f"생성 완료: {out}")
