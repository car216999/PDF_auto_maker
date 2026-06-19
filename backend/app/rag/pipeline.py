"""RAG 파이프라인 — 담당: 박은선.

인덱싱(오프라인): 문서 → 정제 → 청킹 → 중복 제거 → 임베딩 → ChromaDB 저장.
질의(온라인): 컨셉/라벨로 top-k 단일 검색하여 근거 청크 반환.
(중장기: 하이브리드 검색 BM25+벡터 RRF + cross-encoder 리랭킹)

임베딩은 직접 계산해 컬렉션에 주입하므로 ChromaDB 임베딩함수 직렬화 이슈가 없다.
"""
import hashlib
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
        self.persist_dir = Path(persist_dir) if persist_dir else settings.chroma_dir
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    # --- 지연 초기화 (생성만으로는 Ollama·디스크 작업 없음) ---
    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = OllamaEmbedder()
        return self._embedder

    @property
    def client(self):
        if self._client is None:
            import chromadb

            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=chromadb.config.Settings(anonymized_telemetry=False),
            )
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                self.collection_name, metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def _reset_collection(self):
        """컬렉션을 비우고 새로 만든다 (전체 재인덱싱)."""
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._collection = self.client.get_or_create_collection(
            self.collection_name, metadata={"hnsw:space": "cosine"}
        )
        return self._collection

    # --- 인덱싱 ---
    def index(self, docs_dir: Path | str | None = None) -> int:
        """디렉터리의 문서를 인덱싱하고 저장된 청크 수 반환."""
        root = Path(docs_dir) if docs_dir else settings.knowledge_dir
        docs: list[tuple[str, str]] = []
        for pattern in _KNOWLEDGE_GLOBS:
            for path in sorted(root.glob(pattern)):
                docs.append((path.read_text(encoding="utf-8"), path.name))
        return self.index_documents(docs)

    def index_documents(self, docs: list[tuple[str, str]]) -> int:
        """(텍스트, 출처) 목록을 정제·청킹·중복제거 후 저장."""
        ids: list[str] = []
        texts: list[str] = []
        sources: list[str] = []
        seen: set[str] = set()

        for raw, source in docs:
            for i, ch in enumerate(
                chunk_text(clean_text(raw), settings.chunk_size, settings.chunk_overlap)
            ):
                if ch in seen:  # 중복 청크 제거
                    continue
                seen.add(ch)
                ids.append(hashlib.sha1(f"{source}:{i}:{ch}".encode()).hexdigest()[:16])
                texts.append(ch)
                sources.append(source)

        coll = self._reset_collection()
        if not texts:
            return 0
        embeddings = self.embedder.embed(texts)
        coll.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=[{"source": s} for s in sources],
        )
        return len(texts)

    # --- 검색 ---
    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResult:
        k = top_k or settings.top_k
        coll = self.collection
        count = coll.count()
        if count == 0:  # 비어있으면 임베딩 호출 없이 즉시 반환
            return RetrievalResult(query=query, chunks=[])

        emb = self.embedder.embed([query])[0]
        res = coll.query(
            query_embeddings=[emb],
            n_results=min(k, count),
            include=["documents", "metadatas", "distances"],
        )
        chunks: list[RetrievedChunk] = []
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        ):
            meta = meta or {}
            chunks.append(
                RetrievedChunk(
                    text=doc,
                    source=meta.get("source", "unknown"),
                    score=max(0.0, 1.0 - float(dist)),  # 코사인 거리 → 유사도
                    metadata=meta,
                )
            )
        return RetrievalResult(query=query, chunks=chunks)
