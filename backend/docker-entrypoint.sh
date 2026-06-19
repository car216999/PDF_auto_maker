#!/bin/sh
set -e

# 사내 지식 인덱싱 (임베딩 필요 — ollama-init 완료 후 실행됨). 실패해도 서버는 기동.
echo "[entrypoint] indexing knowledge..."
python -m scripts.index_knowledge || echo "[entrypoint] index skipped"

echo "[entrypoint] starting API on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
