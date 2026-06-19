"""시연 스크린샷 생성 — 빈 양식 vs 시스템이 채운 완성 문서.

전체 파이프라인(파싱→RAG→생성→주입)을 돌려 결과를 PNG 로 렌더링한다.
전제: Ollama(qwen3:8b, nomic-embed-text) 가 떠 있어야 함.

사용: uv run python -m scripts.make_screenshots
결과: docs/screenshots/01_blank_form.png, 02_filled_result.png
"""
from pathlib import Path

import fitz

from app.generation.generator import FieldGenerator
from app.injection.injector import PDFInjector
from app.parsing.parser import PDFParser
from app.rag.pipeline import RAGPipeline
from scripts.make_standard_quote import build

ROOT = Path(__file__).resolve().parent.parent.parent
SHOTS = ROOT / "docs" / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)
DPI = 120
# 내용 영역만 잘라 여백 제거 (A4 595x842pt 중 상단 견적서 영역)
CLIP = fitz.Rect(35, 40, 575, 600)


def render(pdf_path: Path, out_png: Path) -> None:
    doc = fitz.open(pdf_path)
    doc[0].get_pixmap(dpi=DPI, clip=CLIP).save(str(out_png))
    doc.close()


# 1) 빈 표준 견적서
src = build(ROOT / "data" / "forms" / "standard_quote.pdf")
render(src, SHOTS / "01_blank_form.png")

# 2) 시스템이 채운 완성 문서
rag = RAGPipeline()
rag.index()
schema = PDFParser().parse(src, "shot")
concept = (
    "주식회사 엑시오가 ABC상사에 보내는 클라우드 서버 구축 견적. "
    "품목 1건: 클라우드 서버 구축, 수량 2대, 단가 300만원. 견적일자 2026-06-19."
)
result = FieldGenerator(rag).generate(schema, concept)
filled = ROOT / "data" / "outputs" / "screenshot_filled.pdf"
PDFInjector(flatten=True).fill(src, result.fields, filled)
render(filled, SHOTS / "02_filled_result.png")

# 3) 기획서 → 사업계획서 신청서 자동 작성 (다른 문서 유형)
from scripts.make_business_plan import build as build_bp

bp_src = build_bp(ROOT / "data" / "forms" / "business_plan.pdf")
bp_schema = PDFParser().parse(bp_src, "bp")
bp_concept = (
    "뚝딱(TookTak) 팀의 오픈소스 LLM·RAG 기반 PDF 양식 자동 작성 시스템 지원사업 신청서를 작성한다. "
    "신청일자는 2026-06-19. 각 항목은 기획서 내용에 근거해 간결하게."
)
bp_result = FieldGenerator(rag).generate(bp_schema, bp_concept)
bp_filled = ROOT / "data" / "outputs" / "screenshot_bp.pdf"
PDFInjector(flatten=True).fill(bp_src, bp_result.fields, bp_filled)
doc = fitz.open(bp_filled)
doc[0].get_pixmap(dpi=DPI, clip=fitz.Rect(35, 45, 560, 610)).save(
    str(SHOTS / "03_business_plan.png"))
doc.close()

print(
    f"견적서 근거율 {result.grounded_ratio:.0%} · "
    f"사업계획서 근거율 {bp_result.grounded_ratio:.0%} · 스크린샷 3장 생성: {SHOTS}"
)
