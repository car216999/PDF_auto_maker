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

    # --- 데이터 경로 ---
    qdrant_dir: Path = PROJECT_ROOT / "data" / "qdrant"  # Qdrant 임베디드 로컬
    forms_dir: Path = PROJECT_ROOT / "data" / "forms"
    knowledge_dir: Path = PROJECT_ROOT / "data" / "knowledge"
    upload_dir: Path = PROJECT_ROOT / "data" / "uploads"
    output_dir: Path = PROJECT_ROOT / "data" / "outputs"


settings = Settings()
