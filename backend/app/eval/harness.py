"""평가 하네스 — 데이터셋을 돌려 기획서 11장 KPI 를 측정.

모든 측정은 동일 양식·동일 입력 세트로 반복해 재현성을 확보한다.
"""
import json
import time
from pathlib import Path

from app.config import settings
from app.eval.metrics import accuracy, field_correct
from app.eval.netguard import NetGuard
from app.generation.generator import FieldGenerator
from app.parsing.parser import PDFParser
from app.rag.pipeline import RAGPipeline

# KPI 합격 기준 (기획서 11장)
KPI_THRESHOLDS = {
    "accuracy": 0.80,
    "time_reduction": 0.50,
    "grounded_ratio": 0.90,
    "external_calls": 0,
}


class EvalHarness:
    def __init__(self, generator=None, parser=None):
        self.parser = parser or PDFParser()
        self.generator = generator or FieldGenerator(RAGPipeline())

    def run_case(self, case: dict, forms_dir: Path) -> dict:
        schema = self.parser.parse(forms_dir / case["form"], form_id=case["id"])

        guard = NetGuard()
        t0 = time.perf_counter()
        with guard.watch():
            result = self.generator.generate(schema, case["concept"])
        elapsed = time.perf_counter() - t0

        pred = {f.name: f.value for f in result.fields}
        correct, total = accuracy(pred, case["gold"])
        manual = case.get("manual_baseline_sec")
        reduction = (1 - elapsed / manual) if manual else None

        return {
            "id": case["id"],
            "fields_total": total,
            "fields_correct": correct,
            "accuracy": correct / total if total else 0.0,
            "grounded_ratio": result.grounded_ratio,
            "system_sec": round(elapsed, 2),
            "manual_baseline_sec": manual,
            "time_reduction": round(reduction, 3) if reduction is not None else None,
            "external_calls": len(guard.external),
            "external_hosts": guard.external,
            "predictions": pred,
            "per_field_correct": {
                k: field_correct(pred.get(k, ""), g) for k, g in case["gold"].items()
            },
        }

    def run(self, dataset_path: Path | str, forms_dir: Path | None = None) -> dict:
        data = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
        forms_dir = forms_dir or settings.forms_dir
        cases = [self.run_case(c, forms_dir) for c in data["cases"]]
        return self._summarize(data["name"], cases)

    def _summarize(self, name: str, cases: list[dict]) -> dict:
        n = len(cases) or 1
        reductions = [c["time_reduction"] for c in cases if c["time_reduction"] is not None]

        metrics = {
            "accuracy": sum(c["accuracy"] for c in cases) / n,
            "grounded_ratio": sum(c["grounded_ratio"] for c in cases) / n,
            "time_reduction": (sum(reductions) / len(reductions)) if reductions else None,
            "external_calls": sum(c["external_calls"] for c in cases),
        }

        kpi = {}
        for key, threshold in KPI_THRESHOLDS.items():
            value = metrics[key]
            if value is None:
                kpi[key] = {"value": None, "threshold": threshold, "pass": None}
            elif key == "external_calls":
                kpi[key] = {"value": value, "threshold": threshold, "pass": value == 0}
            else:
                kpi[key] = {"value": round(value, 3), "threshold": threshold,
                            "pass": value >= threshold}

        return {
            "dataset": name,
            "n_cases": len(cases),
            "kpi": kpi,
            "all_pass": all(v["pass"] for v in kpi.values() if v["pass"] is not None),
            "cases": cases,
        }
