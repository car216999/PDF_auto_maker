"""테스트용 견적서 AcroForm 양식 생성기.

실제 빈 양식 PDF 가 아직 없으므로, 파서·주입 개발/테스트의 고정 픽스처를 만든다.
한글 라벨(좌측) + 입력 필드(우측) 구조로, 파서의 '라벨 위치 추론'을 검증할 수 있다.

사용:  uv run python scripts/make_sample_form.py
결과:  data/forms/sample_quote.pdf
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

# 외부 폰트 파일 없이 한글 출력 (Adobe 한국어 CID 폰트)
KFONT = "HYSMyeongJo-Medium"
pdfmetrics.registerFont(UnicodeCIDFont(KFONT))

# (라벨, 필드명, maxlen) — maxlen 은 추출 검증용
TEXT_ROWS = [
    ("회사명", "company_name", None),
    ("품목", "item", None),
    ("단가", "unit_price", None),
    ("수량", "quantity", 5),
    ("공급가액", "supply_amount", None),
    ("비고", "note", None),
]


def build(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    c.setFont(KFONT, 22)
    c.drawCentredString(width / 2, height - 70, "견 적 서")

    c.setFont(KFONT, 12)
    form = c.acroForm

    y = height - 140
    for label, name, maxlen in TEXT_ROWS:
        c.drawString(80, y + 5, label)
        form.textfield(
            name=name,
            tooltip=label,
            x=190, y=y, width=300, height=24,
            borderStyle="underlined", borderWidth=1, forceBorder=True,
            fontName="Helvetica", fontSize=12,
            maxlen=maxlen,
        )
        y -= 48

    # 체크박스 필드 (타입 추출 검증용)
    c.drawString(80, y + 3, "부가세 포함")
    form.checkbox(
        name="vat_included", tooltip="부가세 포함",
        x=190, y=y, size=20, borderWidth=1, forceBorder=True,
    )

    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent
    out = build(root / "data" / "forms" / "sample_quote.pdf")
    print(f"생성 완료: {out}")
