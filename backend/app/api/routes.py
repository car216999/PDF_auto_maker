"""REST 엔드포인트 — UI 흐름: 업로드 → 컨셉 입력 → 생성 → 미리보기 → 다운로드."""
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app import db
from app.config import settings
from app.schemas.api import (DownloadResponse, FillRequest, GenerateRequest,
                             GenerateResponse, UploadResponse)
from app.services.orchestrator import orchestrator

router = APIRouter(prefix="/api", tags=["tooktak"])


@router.get("/documents/recent")
async def recent_documents(limit: int = 8) -> dict:
    """대시보드 최근 작업 / 문서 관리 목록 — DB 영속화 시 실데이터."""
    return {
        "items": db.recent_documents(limit),
        "count": db.doc_count(),
        "db": db.enabled(),
    }


@router.get("/settings")
async def get_settings() -> dict:
    """설정 페이지 — 시스템 구성·연결 상태(읽기 전용, 온프레미스)."""
    from app.services.orchestrator import orchestrator

    chunks = 0
    try:
        rag = orchestrator.rag
        if rag.client.collection_exists(rag.collection_name):
            chunks = rag.client.count(rag.collection_name).count
    except Exception:
        pass
    ollama_ok = False
    try:
        import urllib.request

        with urllib.request.urlopen(settings.ollama_base_url + "/api/tags", timeout=3) as r:
            ollama_ok = r.status == 200
    except Exception:
        pass
    return {
        "llm_model": settings.llm_model,
        "embed_model": settings.embed_model,
        "vector_db": "Qdrant (임베디드 로컬)",
        "retrieval": "BM25 + BGE-M3 하이브리드(RRF) → cross-encoder 리랭킹",
        "top_k": settings.top_k,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "ollama_url": settings.ollama_base_url,
        "user": settings.default_user_name,
        "chunks": chunks,
        "connections": {
            "Ollama (LLM·임베딩)": ollama_ok,
            "Qdrant (벡터DB)": chunks > 0,
            "PostgreSQL (이력)": db.ping(),
        },
    }


@router.get("/index/stats")
async def index_stats() -> dict:
    """RAG 인덱스 현황 — 청크 수·지식 문서 수·임베딩/벡터DB."""
    from app.services.orchestrator import orchestrator

    chunks = 0
    try:
        rag = orchestrator.rag
        if rag.client.collection_exists(rag.collection_name):
            chunks = rag.client.count(rag.collection_name).count
    except Exception:
        pass
    kdir = settings.knowledge_dir
    kfiles = (len(list(kdir.rglob("*.md"))) + len(list(kdir.rglob("*.txt")))
              if kdir.exists() else 0)
    return {
        "chunks": chunks,
        "knowledge_files": kfiles,
        "embed_model": settings.embed_model,
        "vector_db": "Qdrant",
        "retrieval": "하이브리드(BM25+dense) → cross-encoder 리랭킹",
    }


@router.post("/forms/upload", response_model=UploadResponse)
async def upload_form(file: UploadFile = File(...)) -> UploadResponse:
    """① 빈 양식 PDF 업로드 → 필드 스키마 추출."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "PDF 파일만 업로드할 수 있습니다.")
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    dest = settings.upload_dir / f"{uuid.uuid4().hex[:8]}_{file.filename}"
    dest.write_bytes(await file.read())
    schema = orchestrator.upload(dest)
    return UploadResponse(form=schema)


@router.post("/forms/{form_id}/generate", response_model=GenerateResponse)
async def generate(form_id: str, req: GenerateRequest) -> GenerateResponse:
    """② 컨셉 입력 → 필드별 값 생성 (미리보기용)."""
    try:
        result = orchestrator.generate(form_id, req.concept, req.overrides)
    except KeyError:
        raise HTTPException(404, f"form_id 없음: {form_id}")
    return GenerateResponse(result=result)


@router.post("/forms/{form_id}/download", response_model=DownloadResponse)
async def download(form_id: str, req: FillRequest) -> DownloadResponse:
    """③ 확정값으로 PDF 주입 후 경로 반환."""
    try:
        out = orchestrator.fill(form_id, req.fields)
    except KeyError:
        raise HTTPException(404, f"form_id 없음: {form_id}")
    return DownloadResponse(form_id=form_id, download_path=str(out))


@router.get("/forms/{form_id}/file")
async def get_file(form_id: str) -> FileResponse:
    """채워진 PDF 파일 내려받기."""
    out = settings.output_dir / f"{form_id}_filled.pdf"
    if not out.exists():
        raise HTTPException(404, "생성된 파일이 없습니다. 먼저 download 를 호출하세요.")
    return FileResponse(out, media_type="application/pdf", filename=out.name)
