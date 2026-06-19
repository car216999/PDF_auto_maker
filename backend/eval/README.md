# KPI 평가 하네스

기획서 11장의 정량 목표를 자동 측정한다. 모든 측정은 동일 양식·동일 입력으로 반복해 재현성을 확보.

## 실행

```bash
cd backend
uv run python -m scripts.run_eval
```

전제: Ollama(qwen3:8b, nomic-embed-text) 가 떠 있어야 함. 스크립트가 양식·인덱스를 먼저 보장한다.

## 측정 KPI

| KPI | 방법 | 합격 |
|---|---|---|
| 채움 정확도 | 정답 대비 필드 일치율(정규화 비교) | ≥ 80% |
| 시간 단축 | 1 − 시스템시간/수작업기준 | ≥ 50% |
| 근거 일치율 | `grounded` 비율 | ≥ 90% |
| 외부 호출 0 | 소켓 가로채기로 비-루프백 연결 감지 | 0건 |

## 데이터셋

`eval/datasets/*.json` — 각 케이스: `form`(양식 파일), `concept`(입력),
`manual_baseline_sec`(수작업 기준 시간), `gold`(정답 필드값).
정답은 `data/knowledge/` 의 사내 문서에 근거해 작성한다.

새 양식/시나리오를 추가하려면 케이스를 dataset 에 추가하면 된다.

## 결과

콘솔에 KPI 합격/불합격 요약, `eval/report.json` 에 케이스별 상세(필드별 정오표 포함).
