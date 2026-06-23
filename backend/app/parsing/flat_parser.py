"""평면(비-AcroForm) PDF 필드 감지.

두 가지 패턴을 감지한다:
  1) 인라인  — '라벨 + 오른쪽 빈칸(밑줄)'        예) 회사명 ____  → 밑줄 위에 값
  2) 섹션    — '제목 + 아래 빈 영역(밑줄 없음)'   예) ■ 추진배경 / [빈 공간] → 그 아래 문단

우선순위: 밑줄 있으면 인라인, 없고 아래에 큰 빈 공간이 있으면 섹션, 둘 다 아니면 무시.
양식형 평면 PDF·서술형 기획서 모두 대응. (가이드/문장 라인은 보수적으로 제외)
"""
import re

import fitz

from app.schemas.form import BBox, FieldType, FormField

_LABEL_JOIN_GAP = 14.0
_MIN_SLOT_W = 80.0
_MAX_LABEL_LEN = 20
_MAX_LABEL_WORDS = 5
_RIGHT_MARGIN = 45.0
_SECTION_MIN_GAP = 26.0   # 제목 아래 빈 공간 최소 높이
_SECTION_MAX_H = 75.0     # 섹션 채움 영역 최대 높이


def _clean(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^[■□●▪•◦\-]\s*", "", text)        # 머리 기호 제거
    text = re.sub(r"^(\d+[.)]|[가-힣][.)])\s*", "", text)  # 1. / 가) 등 목록 마커
    return text.rstrip(":：·").strip()


def _looks_like_label(text: str) -> bool:
    if not (2 <= len(text) <= _MAX_LABEL_LEN):
        return False
    if text.endswith((".", ",", "다", "음", "함", "임", "됨")):  # 문장형 제외
        return False
    if re.fullmatch(r"[\d\s.,\-/]+", text):
        return False
    return True


def _horizontal_lines(page: fitz.Page) -> list[tuple[float, float, float]]:
    out: list[tuple[float, float, float]] = []
    for dr in page.get_drawings():
        for it in dr["items"]:
            if it[0] == "l":
                p1, p2 = it[1], it[2]
                if abs(p1.y - p2.y) < 1.5 and abs(p2.x - p1.x) >= _MIN_SLOT_W:
                    out.append((min(p1.x, p2.x), max(p1.x, p2.x), (p1.y + p2.y) / 2))
            elif it[0] == "re":
                r = it[1]
                if r.height < 2 and r.width >= _MIN_SLOT_W:
                    out.append((r.x0, r.x1, (r.y0 + r.y1) / 2))
    return out


def detect_flat_fields(doc: fitz.Document) -> list[FormField]:
    fields: list[FormField] = []
    seen: set[str] = set()

    for pno, page in enumerate(doc):
        right = page.rect.width - _RIGHT_MARGIN
        left_zone = page.rect.width * 0.4
        hlines = _horizontal_lines(page)
        words = page.get_text("words")

        # 폰트 크기 조회용 스팬 (제목 등 큰 글씨 제외)
        spans = [(sp["bbox"], sp["size"])
                 for blk in page.get_text("dict")["blocks"]
                 for ln in blk.get("lines", [])
                 for sp in ln.get("spans", [])]

        def font_size_at(x: float, y: float) -> float:
            for bb, sz in spans:
                if bb[0] - 1 <= x <= bb[2] + 1 and bb[1] - 1 <= y <= bb[3] + 1:
                    return sz
            return 11.0

        # 라인별 그룹 + 라인 bbox
        line_words: dict[tuple, list] = {}
        for w in words:
            line_words.setdefault((w[5], w[6]), []).append(w)
        line_box = {k: (min(w[0] for w in ws), min(w[1] for w in ws),
                        max(w[2] for w in ws), max(w[3] for w in ws))
                    for k, ws in line_words.items()}

        def next_text_top(x0: float, x1: float, y1: float) -> float | None:
            """수평으로 겹치며 아래에 있는 가장 가까운 라인의 상단 y."""
            cands = [b[1] for b in line_box.values()
                     if b[1] > y1 + 1 and not (b[2] < x0 - 2 or b[0] > x1 + 2)]
            return min(cands) if cands else None

        for ws in line_words.values():
            ws.sort(key=lambda w: w[0])
            cluster = [ws[0]]
            for prev, cur in zip(ws, ws[1:]):
                if cur[0] - prev[2] <= _LABEL_JOIN_GAP:
                    cluster.append(cur)
                else:
                    break
            label = _clean(" ".join(w[4] for w in cluster))
            if not _looks_like_label(label) or len(cluster) > _MAX_LABEL_WORDS:
                continue

            x0 = cluster[0][0]
            label_end = cluster[-1][2]
            y0 = min(w[1] for w in cluster)
            y1 = max(w[3] for w in cluster)

            # 1순위: 우측 밑줄 → 인라인 (위치 무관, 밑줄이 필드를 확정)
            cand = [ln for ln in hlines
                    if ln[1] > label_end + 10 and y0 - 4 <= ln[2] <= y1 + 12]
            if cand:
                ln = min(cand, key=lambda l: abs(l[2] - y1))
                bx0, bx1, by0, by1 = ln[0] + 3, ln[1] - 3, ln[2] - 16, ln[2] - 1
            else:
                # 밑줄 없는 항목은 좌측 정렬 + 제목(큰 글씨)이 아니어야 함
                if x0 > left_zone or font_size_at(x0 + 1, (y0 + y1) / 2) > 15:
                    continue
                # 2순위: 제목 아래 빈 영역 → 섹션 (문단)
                nt = next_text_top(x0, right, y1)
                gap = (nt - y1) if nt is not None else _SECTION_MAX_H
                if gap >= _SECTION_MIN_GAP:
                    h = min(gap - 6, _SECTION_MAX_H)
                    bx0, bx1, by0, by1 = x0 + 2, right, y1 + 4, y1 + 4 + h
                else:
                    # 3순위: 우측 빈 공간 → 인라인
                    rest = [w for w in ws if w[0] > label_end + 1]
                    bx0 = label_end + 8
                    bx1 = (rest[0][0] - 4) if rest else right
                    by0, by1 = y0, y1

            if bx1 - bx0 < _MIN_SLOT_W:
                continue
            key = f"{pno}:{round(by0)}:{label}"
            if key in seen:
                continue
            seen.add(key)
            fields.append(FormField(
                name=f"flat_{pno}_{len(fields)}",
                label=label,
                field_type=FieldType.TEXT,
                page=pno,
                bbox=BBox(x0=bx0, y0=by0, x1=bx1, y1=by1),
            ))

    return fields
