"""표 형태(비-AcroForm) 양식 — 약식기획서 표지처럼 라벨 칸 + 값 칸.

표 채우기(셀 격자 인식) 테스트용. 입력 필드는 없고, 선으로 그린 표만 있다.

사용:  uv run python -m scripts.make_table_form
결과:  data/forms/table_form.pdf
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

KFONT = "HYSMyeongJo-Medium"
pdfmetrics.registerFont(UnicodeCIDFont(KFONT))
W, H = A4

# (라벨, 행 높이)
ROWS = [
    ("팀명", 28),
    ("팀원 및 역할", 28),
    ("주제 구분", 28),
    ("기업명 / 멘토명", 28),
    ("아이디어 주제", 28),
    ("제안 배경 및 필요성", 90),
]


def build(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont(KFONT, 16)
    c.drawCentredString(W / 2, H - 70, "프로젝트 개요")

    c.setFont(KFONT, 11)
    x0, xmid, x1 = 70, 200, 525
    y = H - 110
    for label, h in ROWS:
        c.rect(x0, y - h, xmid - x0, h)      # 라벨 칸
        c.rect(xmid, y - h, x1 - xmid, h)    # 값 칸 (빈 칸)
        c.drawString(x0 + 6, y - 17, label)  # 라벨 텍스트
        y -= h

    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent
    out = build(root / "data" / "forms" / "table_form.pdf")
    print(f"생성 완료: {out}")
