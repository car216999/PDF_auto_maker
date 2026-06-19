"""사업계획서(지원사업 신청서) AcroForm 생성기.

기획서 내용으로 채울 신청서 양식. 단일행 필드 + 멀티라인 문단 박스(사업개요·핵심기능·기대효과).
기획서 13장 활용방안 "정부지원사업·사업계획서 초안 자동 완성" 시나리오용.

사용:  uv run python -m scripts.make_business_plan
결과:  data/forms/business_plan.pdf
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

    def box_field(name, x, y, w, h, lab):
        form.textfield(name=name, tooltip=lab, x=x, y=y, width=w, height=h,
                       borderStyle="solid", borderWidth=1, forceBorder=True,
                       fieldFlags="multiline", fontName="Helvetica", fontSize=10)

    # 제목
    c.setFont(KFONT, 22)
    c.drawCentredString(W / 2, H - 60, "사 업 계 획 서")
    c.setFont(KFONT, 10)
    c.drawCentredString(W / 2, H - 80, "( 지원사업 신청서 )")

    # --- 기본 정보 (단일행) ---
    label(65, H - 120 + 4, "사업명")
    line_field("project_title", 150, H - 120, 380, "사업명")

    label(65, H - 150 + 4, "신청팀")
    line_field("team_name", 150, H - 150, 170, "신청팀")
    label(340, H - 150 + 4, "팀장")
    line_field("team_leader", 400, H - 150, 130, "팀장")

    label(65, H - 180 + 4, "팀원")
    line_field("team_members", 150, H - 180, 380, "팀원")

    label(65, H - 210 + 4, "주관·멘토")
    line_field("company_mentor", 150, H - 210, 170, "주관·멘토")
    label(340, H - 210 + 4, "사업분야")
    line_field("category", 400, H - 210, 130, "사업분야")

    label(65, H - 240 + 4, "신청일자")
    line_field("apply_date", 150, H - 240, 170, "신청일자")

    # --- 문단 섹션 (멀티라인) ---
    label(65, H - 278, "■ 사업 개요")
    box_field("summary", 65, H - 345, 465, 58, "사업 개요")

    label(65, H - 365, "■ 핵심 기능")
    box_field("key_features", 65, H - 432, 465, 58, "핵심 기능")

    # --- 단일행 ---
    label(65, H - 455 + 4, "기술 스택")
    line_field("tech_stack", 150, H - 455, 380, "기술 스택")

    label(65, H - 485 + 4, "추진 일정")
    line_field("schedule", 150, H - 485, 380, "추진 일정")

    # --- 문단 ---
    label(65, H - 515, "■ 기대 효과")
    box_field("expected_effect", 65, H - 585, 465, 62, "기대 효과")

    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent
    out = build(root / "data" / "forms" / "business_plan.pdf")
    print(f"생성 완료: {out}")
