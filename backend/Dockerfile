# 뚝딱 백엔드 — FastAPI + PyMuPDF + ChromaDB (uv 기반)
FROM python:3.13-slim

# uv 설치 (공식 이미지에서 복사)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 의존성 먼저 설치 (레이어 캐시 — uv.lock 으로 전원 동일 환경)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 앱 소스
COPY . .

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

# 시작 시 지식 인덱싱 후 서버 기동
RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["./docker-entrypoint.sh"]
