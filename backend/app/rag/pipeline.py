"""RAG 파이프라인 — 담당: 박은선.

벡터스토어: Qdrant(임베디드 로컬, path 모드 → 서버 불필요).
임베딩: BGE-M3(1024d, dense) via Ollama + BM25(sparse) via fastembed.
검색(2단계):
  1) dense(의미) + sparse(어휘) → Qdrant 네이티브 RRF 융합으로 후보 N개 (하이브리드)
  2) cross-encoder(jina multilingual)로 (질의,후보) 직접 채점 → top-k 정밀 재정렬

dense 는 의미 유사, sparse(BM25)는 정확 키워드·번호(선급번호·IMO 등) 매칭에 강하고,
cross-encoder 는 질의-문서를 함께 보고 정밀 채점한다. 견적서·선급 양식처럼 고유명사·
코드가 많은 도메인에 특히 효과적이다.

[로컬 ↔ 서버 전환] QdrantClient(path=...) → QdrantClient(url="http://...:6333") 한 줄.
[끄기] RAGPipeline(hybrid=False, rerank=False) — dense 단일 검색(단위 테스트 등).
"""
from pathlib import Path

from app.config import settings
from app.rag.embeddings import Embedder, OllamaEmbedder
from app.rag.preprocess import chunk_text, clean_text
from app.schemas.rag import RetrievalResult, RetrievedChunk

_KNOWLEDGE_GLOBS = ("*.md", "*.txt")
_DENSE = "dense"
_SPARSE = "sparse"


class RAGPipeline:
    def __init__(
        self,
        embedder: Embedder | None = None,
        persist_dir: Path | str | None = None,
        collection_name: str = "tooktak_knowledge",
        hybrid: bool = True,
        rerank: bool = True,
    ):
        self._embedder = embedder
        self.persist_dir = Path(persist_dir) if persist_dir else settings.qdrant_dir
        self.collection_name = collection_name
        self.hybrid = hybrid
        self.rerank = rerank
        self._client = None
        self._bm25 = None
        self._reranker = None

    # --- 지연 초기화 (생성만으로는 Ollama·디스크 작업 없음) ---
    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = OllamaEmbedder()
        return self._embedder

    @property
    def bm25(self):
        """BM25 sparse 인코더 (fastembed). 모델 캐시는 프로젝트 폴더에 고정."""
        if self._bm25 is None:
            from fastembed import SparseTextEmbedding

            self._bm25 = SparseTextEmbedding(
                "Qdrant/bm25", cache_dir=str(settings.fastembed_dir)
            )
        return self._bm25

    @property
    def reranker(self):
        """cross-encoder 리랭커 (fastembed, onnx). 캐시는 프로젝트 폴더에 고정."""
        if self._reranker is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            self._reranker = TextCrossEncoder(
                settings.rerank_model, cache_dir=str(settings.fastembed_dir)
            )
        return self._reranker

    @property
    def client(self):
        if self._client is None:
            from qdrant_client import QdrantClient

            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = QdrantClient(path=str(self.persist_dir))
        return self._client

    def _sparse_docs(self, texts: list[str]):
        from qdrant_client import models

        out = []
        for e in self.bm25.embed(texts):
            out.append(models.SparseVector(
                indices=[int(i) for i in e.indices],
                values=[float(v) for v in e.values],
            ))
        return out

    def _sparse_query(self, query: str):
        from qdrant_client import models

        e = next(iter(self.bm25.query_embed(query)))
        return models.SparseVector(
            indices=[int(i) for i in e.indices],
            values=[float(v) for v in e.values],
        )

    def _recreate(self, dim: int):
        """컬렉션을 비우고 새로 만든다 (전체 재인덱싱). dense 코사인 + (선택)sparse."""
        from qdrant_client import models

        if self.client.collection_exists(self.collection_name):
            self.client.delete_collection(self.collection_name)
        self.client.create_collection(
            self.collection_name,
            vectors_config={
                _DENSE: models.VectorParams(size=dim, distance=models.Distance.COSINE)
            },
            sparse_vectors_config=(
                {_SPARSE: models.SparseVectorParams()} if self.hybrid else None
            ),
        )

    # --- 인덱싱 ---
    def index(self, docs_dir: Path | str | None = None) -> int:
        root = Path(docs_dir) if docs_dir else settings.knowledge_dir
        docs: list[tuple[str, str]] = []
        for pattern in _KNOWLEDGE_GLOBS:
            for path in sorted(root.rglob(pattern)):  # 하위 폴더까지 재귀
                docs.append((path.read_text(encoding="utf-8"), path.name))
        return self.index_documents(docs)

    def index_documents(self, docs: list[tuple[str, str]]) -> int:
        """(텍스트, 출처) 목록을 정제·청킹·중복제거 후 dense(+sparse) 저장."""
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

        dense = self.embedder.embed(texts)
        sparse = self._sparse_docs(texts) if self.hybrid else None
        self._recreate(len(dense[0]))

        points = []
        for i, (t, s) in enumerate(zip(texts, sources)):
            vec = {_DENSE: dense[i]}
            if sparse is not None:
                vec[_SPARSE] = sparse[i]
            points.append(
                models.PointStruct(id=i, vector=vec, payload={"text": t, "source": s})
            )
        self.client.upsert(self.collection_name, points=points)
        return len(texts)

    # --- 검색 ---
    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResult:
        from qdrant_client import models

        k = top_k or settings.top_k
        # 비어있으면 임베딩 호출 없이 즉시 반환 (오프라인 안전)
        if not self.client.collection_exists(self.collection_name):
            return RetrievalResult(query=query, chunks=[])
        if self.client.count(self.collection_name).count == 0:
            return RetrievalResult(query=query, chunks=[])

        # 1단계: 하이브리드(또는 dense)로 후보 fetch개 (리랭킹 시 더 넓게)
        fetch = settings.rerank_fetch if self.rerank else k
        dense = self.embedder.embed([query])[0]
        if self.hybrid:
            res = self.client.query_points(
                self.collection_name,
                prefetch=[
                    models.Prefetch(query=dense, using=_DENSE, limit=max(fetch, 12)),
                    models.Prefetch(
                        query=self._sparse_query(query), using=_SPARSE,
                        limit=max(fetch, 12),
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=fetch,
                with_payload=True,
            )
        else:
            res = self.client.query_points(
                self.collection_name, query=dense, using=_DENSE,
                limit=fetch, with_payload=True,
            )
        cands = [(p.payload or {}, float(p.score)) for p in res.points]

        # 2단계: cross-encoder 리랭킹 → 정밀 재정렬 (실패 시 1단계 순위 폴백)
        if self.rerank and len(cands) > 1:
            try:
                import math

                scores = list(self.reranker.rerank(query, [m.get("text", "") for m, _ in cands]))
                order = sorted(range(len(cands)), key=lambda i: scores[i], reverse=True)
                cands = [(cands[i][0], 1.0 / (1.0 + math.exp(-scores[i]))) for i in order]
            except Exception:
                pass  # 리랭커 로드/추론 실패 → 하이브리드 순위 그대로
        cands = cands[:k]

        chunks = [
            RetrievedChunk(
                text=m.get("text", ""), source=m.get("source", "unknown"),
                score=max(0.0, s), metadata=m,
            )
            for m, s in cands
        ]
        return RetrievalResult(query=query, chunks=chunks)
