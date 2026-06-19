"""실제 Ollama(qwen3:8b)로 샘플 견적서를 채워보는 데모.

사용: uv run python scripts/try_generate.py
결과: backend/_gen_demo.json (UTF-8)
"""
import json
from pathlib import Path

from app.generation.generator import FieldGenerator
from app.parsing.parser import PDFParser
from app.rag.pipeline import RAGPipeline

ROOT = Path(__file__).resolve().parent.parent.parent
pdf = ROOT / "data" / "forms" / "sample_quote.pdf"

schema = PDFParser().parse(pdf, form_id="demo")
labels = {f.name: f.label for f in schema.fields}

concept = "주식회사 엑시오의 클라우드 서버 구축 견적. 단가 300만원, 수량 2대."
result = FieldGenerator(RAGPipeline()).generate(schema, concept)

report = {
    "concept": concept,
    "model": result.model,
    "grounded_ratio": round(result.grounded_ratio, 2),
    "fields": [
        {"label": labels.get(f.name, f.name), "name": f.name,
         "value": f.value, "grounded": f.grounded}
        for f in result.fields
    ],
}
out = Path(__file__).resolve().parent.parent / "_gen_demo.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", out)
