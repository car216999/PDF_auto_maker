"""사내 지식 문서를 ChromaDB 에 인덱싱.

사용: uv run python -m scripts.index_knowledge
대상: data/knowledge/*.md, *.txt
"""
from app.config import settings
from app.rag.pipeline import RAGPipeline

n = RAGPipeline().index()
print(f"indexed {n} chunks from {settings.knowledge_dir}")
