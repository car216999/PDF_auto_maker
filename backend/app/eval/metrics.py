"""KPI 측정용 순수 함수 — 정답 대비 채움 정확도."""
import re


def normalize(value: str) -> str:
    """비교용 정규화: 공백·쉼표 제거 + 소문자화.

    '300 만원', '300만원', '300,만원' 을 같게 본다. (숫자 단위 변환은 중장기)
    """
    return re.sub(r"[\s,]", "", (value or "").strip()).lower()


def field_correct(pred: str, gold: str) -> bool:
    return normalize(pred) == normalize(gold)


def accuracy(pred: dict[str, str], gold: dict[str, str]) -> tuple[int, int]:
    """(정확 채움 필드 수, 전체 정답 필드 수)."""
    correct = sum(1 for name, g in gold.items() if field_correct(pred.get(name, ""), g))
    return correct, len(gold)
