"""평면(비-AcroForm) 견적서 생성기 — 입력 필드 없이 라벨 + 밑줄만.

평면 PDF 채우기(좌표 오버레이) 테스트용. AcroForm 위젯이 0개라, 라벨 옆 빈 공간을
파서가 감지해 채워야 한다.

사용:  uv run python -m scripts.make_flat_quote
결과:  data/forms/flat_quote.pdf
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

KFONT = "HYSMyeongJo-Medium"
pdfmetrics.registerFont(UnicodeCIDFont(KFONT))
W, H = A4

ROWS = ["회사명", "품목", "단가", "수량", "공급가액", "비고"]


def build(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont(KFONT, 22)
    c.drawCentredString(W / 2, H - 70, "견 적 서")

    c.setFont(KFONT, 12)
    y = H - 140
    for label in ROWS:
        c.drawString(80, y, label)           # 라벨 (텍스트)
        c.line(180, y - 3, 480, y - 3)        # 빈칸 (밑줄 — 그래픽, 입력필드 아님)
        y -= 45
    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent
    out = build(root / "data" / "forms" / "flat_quote.pdf")
    print(f"생성 완료: {out}")
