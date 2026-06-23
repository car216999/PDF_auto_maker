"""RAG 파이프라인 단위 테스트 — 가짜 임베더 + 임시 Qdrant(디스크)로 오프라인 검증.

가짜 임베더는 고정 한국어 키워드 사전 기반 벡터를 만들어, 키워드가 겹치는 청크가
검색 상위에 오도록 한다(의미적 관련성을 결정론적으로 모사).
"""
from app.rag.pipeline import RAGPipeline
from app.rag.preprocess import chunk_text, clean_text

VOCAB = ["회사", "엑시오", "단가", "수량", "공급가액", "부가세", "클라우드", "서버"]


class FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            vec = [float(t.count(w)) for w in VOCAB]
            if not any(vec):  # 영벡터 방지
                vec = [1e-6] * len(VOCAB)
            out.append(vec)
        return out


def _pipeline(tmp_path) -> RAGPipeline:
    return RAGPipeline(
        embedder=FakeEmbedder(),
        persist_dir=tmp_path / "qdrant",
        collection_name="test_kb",
        hybrid=False,  # 단위 테스트는 dense 단일로 결정론 유지
        rerank=False,
    )


def test_clean_text_removes_page_numbers():
    raw = "머리\n- 3 -\n본문 내용\n42\npage 7\n끝"
    cleaned = clean_text(raw)
    assert "본문 내용" in cleaned
    assert "- 3 -" not in cleaned
    assert "page 7" not in cleaned
    assert "\n42\n" not in cleaned


def test_chunk_text_filters_empty():
    chunks = chunk_text("문장 하나.\n\n\n문장 둘.", size=50, overlap=10)
    assert chunks
    assert all(c.strip() for c in chunks)


def test_index_and_retrieve(tmp_path):
    rag = _pipeline(tmp_path)
    n = rag.index_documents([
        ("주식회사 엑시오는 클라우드 서버 구축 전문 회사이다.", "company.md"),
        ("부가세는 공급가액의 10% 이며 부가세 별도로 표기한다.", "tax.md"),
    ])
    assert n >= 2

    res = rag.retrieve("엑시오 클라우드 서버", top_k=2)
    assert res.chunks
    # 가장 관련 높은 청크는 회사 문서
    assert "엑시오" in res.chunks[0].text
    assert res.chunks[0].source == "company.md"
    assert 0.0 <= res.chunks[0].score <= 1.0


def test_dedupe_identical_chunks(tmp_path):
    rag = _pipeline(tmp_path)
    n = rag.index_documents([
        ("같은 문장.", "a.md"),
        ("같은 문장.", "b.md"),  # 동일 내용 → 중복 제거
    ])
    assert n == 1


def test_retrieve_empty_collection_no_embed(tmp_path):
    """비어있는 컬렉션은 임베딩 호출 없이 즉시 빈 결과 (오프라인 안전)."""

    class BoomEmbedder:
        def embed(self, texts):
            raise AssertionError("빈 컬렉션에서는 임베딩을 호출하면 안 됨")

    rag = RAGPipeline(
        embedder=BoomEmbedder(),
        persist_dir=tmp_path / "qdrant",
        collection_name="empty_kb",
        hybrid=False,
        rerank=False,
    )
    res = rag.retrieve("아무거나")
    assert res.chunks == []


def test_reindex_replaces(tmp_path):
    rag = _pipeline(tmp_path)
    rag.index_documents([("첫 문서 내용.", "first.md")])
    rag.index_documents([("두번째 문서 내용.", "second.md")])  # 전체 재인덱싱
    res = rag.retrieve("문서", top_k=5)
    sources = {c.source for c in res.chunks}
    assert sources == {"second.md"}  # 이전 인덱스는 사라짐
