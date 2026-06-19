"""뚝딱(TookTak) 백엔드 진입점.

완전 로컬 구조: 외부 네트워크 호출 0건. LLM·임베딩 모두 로컬 Ollama 사용.
실행:  uv run uvicorn app.main:app --reload
문서:  http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 데이터 디렉터리 보장
    for d in (settings.upload_dir, settings.output_dir,
              settings.forms_dir, settings.knowledge_dir):
        d.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="TookTak — PDF 양식 자동 작성",
    description="오픈소스 LLM·RAG 기반. 빈 양식 + 컨셉 입력 → 완성 문서.",
    version="0.1.0",
    lifespan=lifespan,
)

# React 개발 서버 연동 (Vite 5173 / CRA 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "llm": settings.llm_model, "external_calls": 0}
