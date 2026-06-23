"""전역 설정. 모든 경로·모델명을 한곳에서 관리한다.

기획서 원칙: 외부 API 호출 0건 — LLM·임베딩 모두 로컬 Ollama 사용.
환경변수 TOOKTAK_* 또는 backend/.env 로 덮어쓸 수 있다.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_prefix="TOOKTAK_", extra="ignore"
    )

    # --- Ollama (완전 로컬) ---
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen3:8b"
    embed_model: str = "bge-m3"  # 다국어 임베딩(1024d) — 한국어 강함

    # --- RAG ---
    top_k: int = 4
    chunk_size: int = 800
    chunk_overlap: int = 120
    # 2단계 리랭킹: 하이브리드로 rerank_fetch개 후보 → cross-encoder로 top_k 선별
    rerank_model: str = "jinaai/jina-reranker-v2-base-multilingual"  # onnx, 다국어
    rerank_fetch: int = 20

    # --- DB (선택) — 설정 시 폼·문서 이력 영속화. 없으면 메모리 동작 ---
    db_url: str = ""  # 예: postgresql+psycopg2://user:pw@host:port/db
    default_user_email: str = "the@aeokorea.com"
    default_user_name: str = "김세경"

    # --- 데이터 경로 ---
    qdrant_dir: Path = PROJECT_ROOT / "data" / "qdrant"  # Qdrant 임베디드 로컬
    fastembed_dir: Path = PROJECT_ROOT / "data" / "fastembed"  # BM25 sparse 모델 캐시
    forms_dir: Path = PROJECT_ROOT / "data" / "forms"
    knowledge_dir: Path = PROJECT_ROOT / "data" / "knowledge"
    upload_dir: Path = PROJECT_ROOT / "data" / "uploads"
    output_dir: Path = PROJECT_ROOT / "data" / "outputs"


settings = Settings()
