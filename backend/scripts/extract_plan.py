"""기획서 PDF → RAG 지식 문서(data/knowledge/tooktak_plan.md) 추출.

내용이 있는 기획서를 자동 선택한다(최종기획서 우선, 빈 템플릿이면 약식기획서로 폴백).
빈 템플릿이면 경고만 하고 덮어쓰지 않는다.

[월요일 교체 절차]
  1) 내용을 채운 '최종기획서_뚝딱.pdf' 를 프로젝트 루트에 둔다 (같은 파일명).
  2) uv run python -m scripts.extract_plan          # 자동으로 최종기획서 채택
  3) uv run python -m scripts.run_eval              # KPI 재측정
     uv run python -m scripts.make_screenshots      # 시연 스크린샷 재생성

사용:
  uv run python -m scripts.extract_plan                         # 자동 선택
  uv run python -m scripts.extract_plan --source 최종기획서_뚝딱.pdf  # 명시
"""
import argparse
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "data" / "knowledge" / "tooktak_plan.md"

# 내용 있는 문서를 고를 때 보는 후보 (최종기획서 우선)
CANDIDATES = ["최종기획서_뚝딱.pdf", "약식기획서_뚝딱팀_v3_보강.pdf"]
KEYWORDS = ["뚝딱", "TookTak", "Qwen", "RAG", "견적서", "엑시오",
            "온프레미스", "PyMuPDF", "Qdrant", "김세경"]


def extract_text(pdf: Path) -> str:
    doc = fitz.open(pdf)
    try:
        parts = [p.get_text().strip() for p in doc if p.get_text().strip()]
    finally:
        doc.close()
    return "\n\n".join(parts)


def keyword_hits(text: str) -> int:
    return sum(text.count(k) for k in KEYWORDS)


def pick_source(arg_source: str | None) -> tuple[Path, str]:
    if arg_source:
        p = ROOT / arg_source
        if not p.exists():
            raise SystemExit(f"파일 없음: {p}")
        return p, extract_text(p)

    fallback: tuple[Path, str] | None = None
    for name in CANDIDATES:
        p = ROOT / name
        if not p.exists():
            continue
        text = extract_text(p)
        if keyword_hits(text) > 0:          # 내용 있으면 즉시 채택
            return p, text
        fallback = fallback or (p, text)     # 빈 템플릿은 폴백 후보로만
    if fallback:
        return fallback
    raise SystemExit("기획서 PDF를 찾을 수 없습니다.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=None, help="기획서 PDF 파일명 (프로젝트 루트 기준)")
    args = ap.parse_args()

    src, full = pick_source(args.source)
    hits = keyword_hits(full)

    if hits == 0:
        print(f"[경고] '{src.name}' 에서 프로젝트 키워드 0회 - 빈 템플릿으로 보입니다.")
        print("  내용을 채운 PDF인지 확인하세요. 지식 문서를 덮어쓰지 않았습니다.")
        return

    OUT.write_text(
        f"# 뚝딱(TookTak) 프로젝트 기획서\n\n출처: {src.name}\n\n{full}\n",
        encoding="utf-8",
    )
    print(f"[완료] {src.name} -> {OUT.relative_to(ROOT)}  ({len(full):,}자, 키워드 {hits}회)")
    print("  다음: uv run python -m scripts.run_eval  /  uv run python -m scripts.make_screenshots")


if __name__ == "__main__":
    main()
