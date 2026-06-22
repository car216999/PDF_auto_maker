"""프로젝트 기획서 AcroForm 생성기 — 팀 최종기획서 구조 반영.

최종기획서 목차(1.프로젝트 개요: 추진배경·서비스내용·주요기술·기대효과 / 추진일정)를
서술형 문단 양식으로 구성. 시스템이 기획서 지식으로 각 항목을 자동 작성하는 테스트용.

사용:  uv run python -m scripts.make_project_plan
결과:  data/forms/project_plan.pdf
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

    def line_field(name, x, y, w, lab):
        form.textfield(name=name, tooltip=lab, x=x, y=y, width=w, height=20,
                       borderStyle="underlined", borderWidth=1, forceBorder=True,
                       fontName="Helvetica", fontSize=10)

    def section(name, lab, top_y, h=48):
        label(65, top_y, f"■ {lab}")
        form.textfield(name=name, tooltip=lab, x=65, y=top_y - 8 - h, width=465, height=h,
                       borderStyle="solid", borderWidth=1, forceBorder=True,
                       fieldFlags="multiline", fontName="Helvetica", fontSize=10)

    # 제목
    c.setFont(KFONT, 22)
    c.drawCentredString(W / 2, H - 55, "프로젝트 기획서")

    # 기본 정보
    label(65, H - 100 + 4, "프로젝트명")
    line_field("project_title", 150, H - 100, 380, "프로젝트명")
    label(65, H - 128 + 4, "팀명")
    line_field("team_name", 130, H - 128, 170, "팀명")
    label(340, H - 128 + 4, "팀장")
    line_field("team_leader", 400, H - 128, 130, "팀장")
    label(65, H - 156 + 4, "작성일자")
    line_field("doc_date", 150, H - 156, 170, "작성일자")

    # 서술형 섹션 (멀티라인)
    section("background", "추진배경 및 필요성", H - 185)
    section("service", "서비스 내용", H - 260)
    section("tech", "주요 기술", H - 335)
    section("effect", "기대 효과", H - 410)
    section("schedule", "추진 일정", H - 485)

    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent
    out = build(root / "data" / "forms" / "project_plan.pdf")
    print(f"생성 완료: {out}")
