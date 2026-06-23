"""평면(비-AcroForm) 프로젝트 기획서 — 입력 필드 없이 라벨/섹션 제목 + 빈 영역.

섹션 제목 아래 문단 채우기 모드 테스트용. 상단은 인라인(라벨+밑줄), 본문은 섹션(제목+빈 영역).

사용:  uv run python -m scripts.make_flat_plan
결과:  data/forms/flat_plan.pdf
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

    c.setFont(KFONT, 22)
    c.drawCentredString(W / 2, H - 60, "프로젝트 기획서")

    c.setFont(KFONT, 11)

    # --- 인라인 (라벨 + 밑줄) ---
    def inline(label, lx, line_x0, line_x1, y):
        c.drawString(lx, y, label)
        c.line(line_x0, y - 3, line_x1, y - 3)

    inline("프로젝트명", 70, 160, 525, H - 105)
    inline("팀명", 70, 120, 290, H - 135)
    inline("팀장", 320, 370, 525, H - 135)

    # --- 섹션 (제목 + 아래 빈 영역, 밑줄 없음) ---
    for i, title in enumerate(["■ 추진배경 및 필요성", "■ 서비스 내용",
                               "■ 주요 기술", "■ 기대 효과"]):
        c.setFont(KFONT, 12)
        c.drawString(70, H - 180 - i * 78, title)   # 제목, 아래 ~62pt 빈 영역

    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent
    out = build(root / "data" / "forms" / "flat_plan.pdf")
    print(f"생성 완료: {out}")
