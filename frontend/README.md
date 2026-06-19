# 뚝딱(TookTak) — Frontend

React + Vite 대시보드. 업로드 → 컨셉 입력 → 생성 → 미리보기 → 다운로드.

## 실행

백엔드(:8000)가 먼저 떠 있어야 합니다.

```bash
# 1) 백엔드 (다른 터미널)
cd backend
uv run uvicorn app.main:app --port 8000

# 2) 프론트엔드
cd frontend
npm install      # 최초 1회
npm run dev      # http://localhost:5173
```

`vite.config.js` 의 프록시가 `/api` 요청을 백엔드(:8000)로 전달하므로 CORS 설정 없이 동작합니다.

## 구조

```
src/
├─ main.jsx     진입점
├─ App.jsx      3단계 스텝퍼 (업로드/컨셉/미리보기) + 하위 컴포넌트
├─ api.js       백엔드 REST 호출 래퍼
└─ styles.css   스타일
```

## 흐름

1. **양식 업로드** — 빈 PDF 드래그&드롭 → 백엔드가 필드 추출
2. **컨셉 입력** — 추출된 필드 확인 + 문서 컨셉 입력 → 로컬 LLM 생성
3. **미리보기** — 값 직접 수정 가능. `근거`(사내 문서 기반) / `추론`(모델 계산) 구분 표시 → PDF 생성·다운로드
