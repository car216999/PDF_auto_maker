"""RAG 파이프라인 — 담당: 박은선.

벡터스토어: Qdrant(임베디드 로컬, path 모드 → 서버 불필요).
임베딩: BGE-M3(1024d, 다국어) via Ollama.

인덱싱(오프라인): 문서 → 정제 → 청킹 → 중복 제거 → 임베딩 → Qdrant 저장.
질의(온라인): 컨셉/라벨로 top-k 코사인 검색하여 근거 청크 반환.

[로컬 ↔ 서버 전환] QdrantClient(path=...) → QdrantClient(url="http://...:6333") 한 줄.
(중장기: BGE-M3 dense+sparse 하이브리드 검색 RRF + cross-encoder 리랭킹)
"""
from pathlib import Path

from app.config import settings
from app.rag.embeddings import Embedder, OllamaEmbedder
from app.rag.preprocess import chunk_text, clean_text
from app.schemas.rag import RetrievalResult, RetrievedChunk

_KNOWLEDGE_GLOBS = ("*.md", "*.txt")


class RAGPipeline:
    def __init__(
        self,
        embedder: Embedder | None = None,
        persist_dir: Path | str | None = None,
        collection_name: str = "tooktak_knowledge",
    ):
        self._embedder = embedder
        self.persist_dir = Path(persist_dir) if persist_dir else settings.qdrant_dir
        self.collection_name = collection_name
        self._client = None

    # --- 지연 초기화 (생성만으로는 Ollama·디스크 작업 없음) ---
    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = OllamaEmbedder()
        return self._embedder

    @property
    def client(self):
        if self._client is None:
            from qdrant_client import QdrantClient

            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = QdrantClient(path=str(self.persist_dir))
        return self._client

    def _recreate(self, dim: int):
        """컬렉션을 비우고 새로 만든다 (전체 재인덱싱). 코사인 거리."""
        from qdrant_client import models

        if self.client.collection_exists(self.collection_name):
            self.client.delete_collection(self.collection_name)
        self.client.create_collection(
            self.collection_name,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )

    # --- 인덱싱 ---
    def index(self, docs_dir: Path | str | None = None) -> int:
        """디렉터리의 문서를 인덱싱하고 저장된 청크 수 반환."""
        root = Path(docs_dir) if docs_dir else settings.knowledge_dir
        docs: list[tuple[str, str]] = []
        for pattern in _KNOWLEDGE_GLOBS:
            for path in sorted(root.rglob(pattern)):  # 하위 폴더까지 재귀
                docs.append((path.read_text(encoding="utf-8"), path.name))
        return self.index_documents(docs)

    def index_documents(self, docs: list[tuple[str, str]]) -> int:
        """(텍스트, 출처) 목록을 정제·청킹·중복제거 후 저장."""
        from qdrant_client import models

        texts: list[str] = []
        sources: list[str] = []
        seen: set[str] = set()

        for raw, source in docs:
            for ch in chunk_text(
                clean_text(raw), settings.chunk_size, settings.chunk_overlap
            ):
                if ch in seen:  # 중복 청크 제거
                    continue
                seen.add(ch)
                texts.append(ch)
                sources.append(source)

        if not texts:
            if self.client.collection_exists(self.collection_name):
                self.client.delete_collection(self.collection_name)
            return 0

        embeddings = self.embedder.embed(texts)
        self._recreate(len(embeddings[0]))
        self.client.upsert(
            self.collection_name,
            points=[
                models.PointStruct(id=i, vector=emb, payload={"text": t, "source": s})
                for i, (t, s, emb) in enumerate(zip(texts, sources, embeddings))
            ],
        )
        return len(texts)

    # --- 검색 ---
    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResult:
        k = top_k or settings.top_k
        # 비어있으면 임베딩 호출 없이 즉시 반환 (오프라인 안전)
        if not self.client.collection_exists(self.collection_name):
            return RetrievalResult(query=query, chunks=[])
        if self.client.count(self.collection_name).count == 0:
            return RetrievalResult(query=query, chunks=[])

        emb = self.embedder.embed([query])[0]
        res = self.client.query_points(
            self.collection_name, query=emb, limit=k, with_payload=True
        )
        chunks: list[RetrievedChunk] = []
        for p in res.points:
            meta = p.payload or {}
            chunks.append(
                RetrievedChunk(
                    text=meta.get("text", ""),
                    source=meta.get("source", "unknown"),
                    score=max(0.0, float(p.score)),  # 코사인 유사도
                    metadata=meta,
                )
            )
        return RetrievalResult(query=query, chunks=chunks)
