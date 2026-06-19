"""평가 하네스 단위 테스트 — 가짜 생성기/파서로 Ollama 없이 KPI 계산 검증."""
import socket

from app.eval.harness import EvalHarness
from app.eval.metrics import accuracy, field_correct, normalize
from app.eval.netguard import NetGuard, is_local
from app.schemas.form import FormField, FormSchema
from app.schemas.generation import FilledField, GenerationResult


# --- metrics ---
def test_normalize_and_field_correct():
    assert normalize("300 만원") == normalize("300만원")
    assert field_correct("주식회사 엑시오", "주식회사  엑시오") is True
    assert field_correct("600만원", "500만원") is False


def test_accuracy_counts():
    pred = {"a": "x", "b": "y", "c": "wrong"}
    gold = {"a": "x", "b": "y", "c": "z"}
    correct, total = accuracy(pred, gold)
    assert (correct, total) == (2, 3)


# --- netguard ---
def test_is_local():
    assert is_local("127.0.0.1") is True
    assert is_local("::1") is True
    assert is_local("localhost") is True
    assert is_local("142.250.0.1") is False  # 외부


def test_netguard_records_external():
    guard = NetGuard()
    with guard.watch():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        try:
            s.connect(("203.0.113.7", 80))  # 외부(문서용 IP) — 연결 실패해도 기록은 됨
        except Exception:
            pass
        finally:
            s.close()
    assert "203.0.113.7" in guard.external


# --- harness (가짜 의존성 주입) ---
class FakeParser:
    def parse(self, path, form_id):
        return FormSchema(
            form_id=form_id, filename="q.pdf", page_count=1,
            fields=[FormField(name="company_name", label="회사명"),
                    FormField(name="supply_amount", label="공급가액")],
        )


class FakeGenerator:
    """gold 대로 채우되 supply_amount 만 일부러 틀리게 → 정확도 0.5 검증."""
    def generate(self, form, concept, overrides=None):
        return GenerationResult(
            form_id=form.form_id, model="fake",
            fields=[
                FilledField(name="company_name", value="주식회사 엑시오", grounded=True),
                FilledField(name="supply_amount", value="틀린값", grounded=True),
            ],
        )


def test_run_case_metrics(tmp_path):
    harness = EvalHarness(generator=FakeGenerator(), parser=FakeParser())
    case = {
        "id": "c1", "form": "q.pdf",
        "concept": "엑시오 견적", "manual_baseline_sec": 100,
        "gold": {"company_name": "주식회사 엑시오", "supply_amount": "600만원"},
    }
    r = harness.run_case(case, tmp_path)
    assert r["fields_correct"] == 1
    assert r["fields_total"] == 2
    assert r["accuracy"] == 0.5
    assert r["grounded_ratio"] == 1.0
    assert r["external_calls"] == 0          # 가짜 생성기는 네트워크 없음
    assert r["time_reduction"] is not None   # baseline 있으니 계산됨


def test_summarize_kpi_pass_fail():
    harness = EvalHarness(generator=FakeGenerator(), parser=FakeParser())
    cases = [{
        "id": "c1", "fields_total": 2, "fields_correct": 2, "accuracy": 1.0,
        "grounded_ratio": 0.95, "system_sec": 1.0, "manual_baseline_sec": 100,
        "time_reduction": 0.99, "external_calls": 0, "external_hosts": [],
        "predictions": {}, "per_field_correct": {},
    }]
    summary = harness._summarize("t", cases)
    assert summary["kpi"]["accuracy"]["pass"] is True
    assert summary["kpi"]["grounded_ratio"]["pass"] is True
    assert summary["kpi"]["time_reduction"]["pass"] is True
    assert summary["kpi"]["external_calls"]["pass"] is True
    assert summary["all_pass"] is True
