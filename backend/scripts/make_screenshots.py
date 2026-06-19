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

print(f"근거율 {result.grounded_ratio:.0%} · 스크린샷 2장 생성: {SHOTS}")
