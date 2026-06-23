"""E2E 스모크 테스트: 업로드 → 생성 → 주입 경로가 스텁으로도 끝까지 도는지 검증.

기획서 테스트 전략의 '통합 테스트(업로드→생성→다운로드 전 구간)' 골격.
실제 모듈이 들어와도 이 테스트는 계약(스키마)이 유지되는 한 그대로 통과해야 한다.
"""
from fastapi.testclient import TestClient

from app.main import app
from scripts.make_sample_form import build

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["external_calls"] == 0  # 완전 로컬 불변식


def test_end_to_end_stub(tmp_path, monkeypatch):
    pdf = build(tmp_path / "sample_quote.pdf")  # 실제 AcroForm 양식

    # 생성·검색 단계는 가짜로 — 스모크 테스트는 Ollama·Qdrant 에 의존하지 않음
    from app.schemas.rag import RetrievalResult
    from app.services.orchestrator import orchestrator

    class _FakeLLM:
        def complete(self, prompt, json_mode=True):
            return "{}"

    class _FakeRAG:
        def retrieve(self, query, top_k=None):
            return RetrievalResult(query=query, chunks=[])

    monkeypatch.setattr(orchestrator.generator, "_llm", _FakeLLM())
    monkeypatch.setattr(orchestrator.generator, "rag", _FakeRAG())

    # ① 업로드 → 필드 스키마
    up = client.post(
        "/api/forms/upload",
        files={"file": ("sample_quote.pdf", pdf.read_bytes(), "application/pdf")},
    )
    assert up.status_code == 200
    form = up.json()["form"]
    form_id = form["form_id"]
    assert len(form["fields"]) > 0

    # ② 생성 → 필드 수 일치
    gen = client.post(
        f"/api/forms/{form_id}/generate",
        json={"concept": "엑시오 클라우드 구축 견적", "overrides": {}},
    )
    assert gen.status_code == 200
    fields = gen.json()["result"]["fields"]
    assert len(fields) == len(form["fields"])

    # ③ 주입 → 다운로드 경로
    dl = client.post(f"/api/forms/{form_id}/download", json={"fields": fields})
    assert dl.status_code == 200
    assert dl.json()["form_id"] == form_id


def test_generate_unknown_form_404():
    r = client.post("/api/forms/nope/generate", json={"concept": "x", "overrides": {}})
    assert r.status_code == 404
