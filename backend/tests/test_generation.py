"""생성 모듈 단위 테스트 — 가짜 LLM·RAG 주입으로 Ollama 없이 로직만 빠르게 검증."""
import json

from app.generation.generator import FieldGenerator, _is_grounded
from app.generation.prompts import build_prompt, parse_json_values
from app.schemas.form import FieldType, FormField, FormSchema
from app.schemas.rag import RetrievalResult, RetrievedChunk


class FakeLLM:
    """주어진 매핑을 JSON 으로 돌려주는 가짜 LLM. 호출 프롬프트를 기록."""

    def __init__(self, mapping: dict):
        self.mapping = mapping
        self.calls: list[str] = []

    def complete(self, prompt: str, json_mode: bool = True) -> str:
        self.calls.append(prompt)
        return json.dumps(self.mapping, ensure_ascii=False)


class FakeRAG:
    """고정 근거를 돌려주는 가짜 RAG (Ollama·ChromaDB 불필요)."""

    def __init__(self, text: str = "표준 단가는 300만원이며 부가세 별도이다."):
        self.text = text

    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResult:
        return RetrievalResult(
            query=query,
            chunks=[RetrievedChunk(text=self.text, source="stub://g.md", score=0.9)],
        )


def _form() -> FormSchema:
    return FormSchema(
        form_id="f1", filename="q.pdf", page_count=1,
        fields=[
            FormField(name="company_name", label="회사명"),
            FormField(name="supply_amount", label="공급가액"),
            FormField(name="vat_included", label="부가세 포함", field_type=FieldType.CHECKBOX),
        ],
    )


def test_generate_fills_from_llm():
    llm = FakeLLM({"company_name": "(주)엑시오", "supply_amount": "600만원", "vat_included": "Y"})
    res = FieldGenerator(FakeRAG(), llm=llm).generate(_form(), "엑시오 클라우드 견적")
    vals = {f.name: f.value for f in res.fields}
    assert vals["company_name"] == "(주)엑시오"
    assert vals["supply_amount"] == "600만원"
    assert vals["vat_included"] == "Y"
    assert res.model  # 모델명 기록됨
    assert len(llm.calls) == 1  # 단일 호출로 전체 채움


def test_overrides_skip_llm():
    llm = FakeLLM({"company_name": "무시되어야_함"})
    res = FieldGenerator(FakeRAG(), llm=llm).generate(
        _form(), "x",
        overrides={"company_name": "직접입력", "supply_amount": "100", "vat_included": "N"},
    )
    vals = {f.name: f.value for f in res.fields}
    assert vals["company_name"] == "직접입력"
    assert vals["supply_amount"] == "100"
    assert llm.calls == []  # 전부 override → LLM 미호출


def test_grounding_flag():
    # FakeRAG 근거에 "300만원" 이 포함됨
    llm = FakeLLM({"company_name": "엑시오", "supply_amount": "300만원", "vat_included": "Y"})
    res = FieldGenerator(FakeRAG(), llm=llm).generate(_form(), "엑시오")
    g = {f.name: f.grounded for f in res.fields}
    assert g["supply_amount"] is True            # 근거에 존재 → grounded
    assert 0.0 <= res.grounded_ratio <= 1.0


def test_grounding_includes_concept():
    """사내 문서에 없어도 사용자 컨셉에 있는 값은 grounded (환각 아님)."""
    llm = FakeLLM({"company_name": "ABC상사", "supply_amount": "", "vat_included": ""})
    res = FieldGenerator(FakeRAG(text="무관한 근거"), llm=llm).generate(_form(), "수신은 ABC상사")
    g = {f.name: f.grounded for f in res.fields}
    assert g["company_name"] is True
    assert res.grounded_ratio == 1.0  # 빈 필드 제외, 채운 값(ABC상사)은 grounded


def test_is_grounded_helper():
    ev = "표준 단가는 300만원이며 부가세 별도이다."
    assert _is_grounded("300만원", ev) is True
    assert _is_grounded("9999억원", ev) is False
    assert _is_grounded("", ev) is False


def test_parse_json_values_robust():
    assert parse_json_values('{"a": "1", "b": "2"}') == {"a": "1", "b": "2"}
    # 코드펜스 + 잡텍스트 섞여도 추출
    assert parse_json_values('```json\n{"a": "1"}\n```') == {"a": "1"}
    assert parse_json_values('설명...\n{"a": "x"}\n끝') == {"a": "x"}
    assert parse_json_values("not json") == {}
    # null 은 빈 문자열로
    assert parse_json_values('{"a": null}') == {"a": ""}


def test_build_prompt_contains_fields_and_evidence():
    fields = [FormField(name="company_name", label="회사명")]
    p = build_prompt("엑시오 견적", fields, "근거: 단가 300만원")
    assert "company_name" in p and "회사명" in p
    assert "엑시오 견적" in p
    assert "300만원" in p
