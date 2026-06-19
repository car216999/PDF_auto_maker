"""전처리 — 기획서 9장 절차. 텍스트 정제 + 청킹.

생성 로직과 분리해 단위 테스트가 쉽다.
"""
import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

# "3", "- 3 -", "— 3 —", "page 3" 처럼 페이지 번호만 있는 줄
_PAGE_NUM = re.compile(r"^[\-—–\s]*(page\s*)?\d+[\-—–\s]*$", re.IGNORECASE)


def clean_text(text: str) -> str:
    """머리말·꼬리말·페이지 번호 등 노이즈 제거 + 공백 정리."""
    kept: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if _PAGE_NUM.match(s):  # 페이지 번호 줄 제거
            continue
        kept.append(s)
    # 빈 줄 3개 이상 → 2개로 축소
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """한국어 친화 구분자로 청킹. 빈 청크는 제외."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", ".", " ", ""],
    )
    return [c.strip() for c in splitter.split_text(text) if c.strip()]
