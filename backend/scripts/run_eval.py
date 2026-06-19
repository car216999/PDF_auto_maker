"""KPI 평가 실행 — 기획서 11장 합격 기준 대비 측정 (여러 양식).

사용: uv run python -m scripts.run_eval
결과: 콘솔 요약 + backend/eval/report.json (상세)
"""
import json
from pathlib import Path

from app.eval.harness import EvalHarness
from app.rag.pipeline import RAGPipeline
from scripts.make_sample_form import build as build_sample
from scripts.make_standard_quote import build as build_standard

ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = Path(__file__).resolve().parent.parent
DATASETS = ["quote_basic.json", "standard_quote.json"]

LABELS = {
    "accuracy": "field-fill accuracy",
    "time_reduction": "time reduction",
    "grounded_ratio": "grounding ratio",
    "external_calls": "external API calls",
}


def print_summary(rep: dict) -> None:
    print(f"\ndataset: {rep['dataset']}  (cases: {rep['n_cases']})")
    print("-" * 56)
    for key, k in rep["kpi"].items():
        val, thr, ok = k["value"], k["threshold"], k["pass"]
        if key == "external_calls":
            shown, target = str(val), f"== {thr}"
        else:
            shown = "n/a" if val is None else f"{val:.0%}"
            target = f">= {thr:.0%}"
        status = "PASS" if ok else ("FAIL" if ok is False else "N/A")
        print(f"  {LABELS[key]:22} {shown:>6}   (target {target:>7})  {status}")
    print("-" * 56)
    print(f"  OVERALL: {'ALL PASS' if rep['all_pass'] else 'SOME FAIL'}")


# 재현성: 양식·인덱스를 보장
build_sample(ROOT / "data" / "forms" / "sample_quote.pdf")
build_standard(ROOT / "data" / "forms" / "standard_quote.pdf")
indexed = RAGPipeline().index()
print(f"[setup] indexed {indexed} knowledge chunks")

harness = EvalHarness()
reports = []
for name in DATASETS:
    rep = harness.run(BACKEND / "eval" / "datasets" / name)
    reports.append(rep)
    print_summary(rep)

(BACKEND / "eval" / "report.json").write_text(
    json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"\ndetailed report -> {BACKEND / 'eval' / 'report.json'}")
