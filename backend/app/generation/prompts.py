"""프롬프트 구성 + 응답 파싱. 생성 로직과 분리해 단위 테스트가 쉽다."""
import json
import re

from app.schemas.form import FormField

SYSTEM = (
    "너는 한국어 비즈니스 양식을 채우는 어시스턴트다. "
    "주어진 '컨셉'과 '근거 자료'에 근거해 각 항목 값을 정한다. "
    "근거에 없는 사실은 지어내지 말고, 알 수 없으면 빈 문자열로 둔다. "
    "금액·수량은 숫자 위주로 쓰고, 공급가액처럼 계산 가능한 값은 근거의 단가·수량으로 계산한다."
)


def build_prompt(concept: str, fields: list[FormField], evidence: str) -> str:
    """채울 필드 목록 + 근거를 담은 단일 프롬프트."""
    field_lines = "\n".join(
        f'- "{f.name}": {f.label or f.name} ({f.field_type.value})' for f in fields
    )
    evidence_block = evidence.strip() or "(근거 자료 없음)"
    return f"""{SYSTEM}

[컨셉]
{concept}

[근거 자료]
{evidence_block}

[채울 항목]  (필드명: 라벨)
{field_lines}

[출력 형식]
각 필드명을 key, 채울 값을 문자열 value 로 하는 JSON 객체 하나만 출력한다.
체크박스 항목은 "Y" 또는 "N". 값을 알 수 없으면 "".
설명·코드펜스 없이 JSON 만 출력한다."""


def parse_json_values(raw: str) -> dict[str, str]:
    """LLM 응답(JSON)을 {필드명: 값} 으로. 코드펜스·잡텍스트에 견고하게."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()

    data = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                data = None

    if not isinstance(data, dict):
        return {}
    return {str(k): ("" if v is None else str(v)) for k, v in data.items()}
