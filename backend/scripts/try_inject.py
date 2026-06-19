"""주입 데모 + 검증: 샘플 견적서에 한글 값을 채우고 결과를 확인.

사용: uv run python -m scripts.try_inject
결과: data/outputs/demo_filled.pdf + backend/_inject_report.json
"""
import json
from pathlib import Path

import fitz

from app.injection.injector import PDFInjector
from app.schemas.generation import FilledField
from scripts.make_sample_form import build

ROOT = Path(__file__).resolve().parent.parent.parent

src = build(ROOT / "data" / "forms" / "sample_quote.pdf")
fields = [
    FilledField(name="company_name", value="주식회사 엑시오"),
    FilledField(name="item", value="클라우드 서버 구축"),
    FilledField(name="unit_price", value="300만원"),
    FilledField(name="quantity", value="2"),
    FilledField(name="supply_amount", value="600만원"),
    FilledField(name="note", value="부가세 별도"),
    FilledField(name="vat_included", value="N"),
]

out = ROOT / "data" / "outputs" / "demo_filled.pdf"
PDFInjector(flatten=True).fill(src, fields, out)

# --- 검증: 출력 PDF 에서 텍스트 추출 + 위젯 잔존 여부 ---
doc = fitz.open(out)
text = "\n".join(page.get_text() for page in doc)
widgets_left = sum(len(list(p.widgets() or [])) for p in doc)
is_form = doc.is_form_pdf
doc.close()

report = {
    "output": str(out),
    "size_bytes": out.stat().st_size,
    "widgets_remaining": widgets_left,
    "is_form_after_flatten": is_form,
    "korean_values_found": {
        v: (v in text)
        for v in ["주식회사 엑시오", "클라우드 서버 구축", "300만원", "600만원", "부가세 별도"]
    },
    "extracted_text": text,
}
report_path = Path(__file__).resolve().parent.parent / "_inject_report.json"
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", report_path)
