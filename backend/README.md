# 뚝딱(TookTak) — Backend

오픈소스 LLM·RAG 기반 PDF 양식 자동 작성 시스템. **외부 호출 0건, 완전 로컬.**

## 빠른 시작

```bash
cd backend
uv sync                       # 의존성 설치 (uv.lock 으로 전원 동일 환경)
uv run uvicorn app.main:app --reload
# → http://localhost:8000/docs  (Swagger UI)
```

전제: 로컬에 Ollama 가 떠 있고 `qwen3:8b` 모델이 받아져 있어야 함
(`ollama pull qwen3:8b`, RAG 용은 `ollama pull nomic-embed-text`).

## 폴더 구조 — 모듈 = 담당자

```
app/
├─ schemas/      ★ 인터페이스 계약 (4명 공유, 먼저 합의)
│   ├─ form.py        FormField/FormSchema   ← 채요한
│   ├─ rag.py         RetrievedChunk         ← 박은선
│   ├─ generation.py  FilledField            ← 이권형
│   └─ api.py         요청/응답               ← 김세경
├─ parsing/      PDF 파싱·폼필드 추출         ← 채요한
├─ rag/          청킹·임베딩·검색             ← 박은선
├─ generation/   Ollama 생성                 ← 이권형
├─ injection/    AcroForm 채움·평탄화         ← 이권형/채요한
├─ services/     오케스트레이션·저장소         ← 김세경(통합)
├─ api/          REST 엔드포인트
└─ main.py       FastAPI 진입점
```

## 처리 흐름 (End-to-End)

```
업로드 → PDF 파싱 → RAG 검색 → LLM 생성 → 좌표 주입 → 미리보기/다운로드
 (api)   (parsing)   (rag)     (generation) (injection)
```

지금은 각 모듈이 **스텁**이지만 위 경로 전체가 동작한다(최소 동작 산출물).
담당자는 자기 모듈의 `TODO(이름)` 부분만 실제 구현으로 교체하면 되고,
스키마(계약)를 바꾸지 않는 한 다른 모듈에 영향이 없다.

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/forms/upload` | 빈 양식 업로드 → 필드 스키마 |
| POST | `/api/forms/{id}/generate` | 컨셉 입력 → 필드값 생성(미리보기) |
| POST | `/api/forms/{id}/download` | 확정값 주입 → 경로 반환 |
| GET  | `/api/forms/{id}/file` | 채워진 PDF 내려받기 |
| GET  | `/health` | 상태 + 외부 호출 0건 확인 |

## 테스트

```bash
uv run pytest -q
```
