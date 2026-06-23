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


def _is_filler(s: str) -> bool:
    """값칸 placeholder 글자(점선·언더바·U+FDxx 등) — 실제 내용 아님."""
    s = s.strip()
    return bool(s) and all(0xFD00 <= ord(c) <= 0xFDFF or c in "._·…―—-‥∙•" for c in s)


def _is_heading(raw: str) -> bool:
    """머리기호/번호로 시작하는 제목·소제목 (옆에 값을 채우면 안 됨)."""
    raw = raw.strip()
    return bool(re.match(r"^[■□●▪◦▶]|^\d+\s*[.)]|^[가-힣]\s*[.)]", raw))


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


def _table_fields(page: fitz.Page, pno: int, start: int):
    """표(셀 격자) 감지 → '글자 있는 라벨 칸 + 옆 빈 값 칸' 짝지어 필드 생성.

    반환: (필드 목록, 표 셀 영역 목록[라인 감지 제외용]).
    """
    fields: list[FormField] = []
    occupied: list[tuple] = []
    try:
        # 선(테두리) 기반 우선 — 선이 있는 양식에 강함. 없으면 기본(텍스트) 전략
        tabs = page.find_tables(strategy="lines")
        if not getattr(tabs, "tables", []):
            tabs = page.find_tables()
    except Exception:
        return fields, occupied

    words = page.get_text("words")

    def label_ok(label: str) -> bool:
        return (2 <= len(label) <= 40
                and not re.fullmatch(r"[\d\s.,\-/:()]+", label))

    n = start
    for tab in getattr(tabs, "tables", []):
        try:
            data = tab.extract()
        except Exception:
            continue
        for ri, row in enumerate(tab.rows):
            cells = row.cells
            texts = data[ri] if ri < len(data) else []
            real = [(cells[ci], (texts[ci] or "").strip() if ci < len(texts) else "")
                    for ci in range(len(cells)) if cells[ci]]
            for c, _ in real:
                occupied.append(tuple(c))

            used = set()
            # 패턴 A: 한 칸 안의 '라벨 : ___' — 콜론 뒤 빈 공간을 값 슬롯으로
            for idx, (cell, tx) in enumerate(real):
                if not tx or (":" not in tx and "：" not in tx):
                    continue
                cx0, cy0, cx1, cy1 = cell
                inw = [w for w in words
                       if cx0 - 1 <= w[0] and w[2] <= cx1 + 1
                       and cy0 - 1 <= w[1] and w[3] <= cy1 + 1]
                colon_x = max((w[2] for w in inw if ":" in w[4] or "：" in w[4]),
                              default=max((w[2] for w in inw), default=cx0))
                if cx1 - colon_x < 40:
                    continue
                label = _clean(re.split(r"[:：]", tx)[0])
                if label_ok(label):
                    fields.append(FormField(
                        name=f"tbl_{pno}_{n}", label=label, page=pno,
                        bbox=BBox(x0=colon_x + 4, y0=cy0 + 2, x1=cx1 - 4, y1=cy1 - 2)))
                    n += 1
                    used.add(idx)

            # 패턴 B: '라벨 칸 + 옆 빈 값 칸' (None 건너뛴 다음 칸)
            j = 0
            while j < len(real) - 1:
                (bb, tx), (nb, ntx) = real[j], real[j + 1]
                if j not in used and tx and not ntx and ":" not in tx and "：" not in tx:
                    label = _clean(tx)
                    x0, y0, x1, y1 = nb
                    if label_ok(label) and x1 - x0 >= 40:
                        fields.append(FormField(
                            name=f"tbl_{pno}_{n}", label=label, page=pno,
                            bbox=BBox(x0=x0 + 4, y0=y0 + 2, x1=x1 - 4, y1=y1 - 2)))
                        n += 1
                    j += 2
                else:
                    j += 1
    return fields, occupied


def _inside(rects: list[tuple], x: float, y: float) -> bool:
    return any(r[0] - 1 <= x <= r[2] + 1 and r[1] - 1 <= y <= r[3] + 1 for r in rects)


def detect_flat_fields(doc: fitz.Document) -> list[FormField]:
    fields: list[FormField] = []
    seen: set[str] = set()

    for pno, page in enumerate(doc):
        right = page.rect.width - _RIGHT_MARGIN
        left_zone = page.rect.width * 0.4
        hlines = _horizontal_lines(page)
        words = page.get_text("words")

        # 1) 표 칸 채우기 (라벨 칸 + 값 칸)
        tfields, occupied = _table_fields(page, pno, len(fields))
        fields.extend(tfields)

        # 폰트 메타(크기·굵기) — 제목/소제목 판별용 (flag 16 = bold)
        spans = [(sp["bbox"], sp["size"], bool(sp["flags"] & 16))
                 for blk in page.get_text("dict")["blocks"]
                 for ln in blk.get("lines", [])
                 for sp in ln.get("spans", [])]

        def font_meta_at(x: float, y: float) -> tuple[float, bool]:
            for bb, sz, bold in spans:
                if bb[0] - 1 <= x <= bb[2] + 1 and bb[1] - 1 <= y <= bb[3] + 1:
                    return sz, bold
            return 11.0, False

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

            # 콜론 인라인: 한 줄 안 '라벨 : ___' (표 밖, 이중언어 긴 라벨 허용)
            if ws[0][0] <= left_zone and any(":" in w[4] or "：" in w[4] for w in ws):
                cw = next(w for w in ws if ":" in w[4] or "：" in w[4])
                before = [w for w in ws if w[2] <= cw[2]]
                clabel = _clean(re.split(r"[:：]", " ".join(w[4] for w in before))[0])
                ly0 = min(w[1] for w in before)
                ly1 = max(w[3] for w in before)
                after = [w for w in ws if w[0] > cw[2] + 1 and not _is_filler(w[4])]
                sx1 = (after[0][0] - 4) if after else right
                if (2 <= len(clabel) <= 40 and sx1 - cw[2] >= 40
                        and not re.fullmatch(r"[\d\s.,\-/:()]+", clabel)
                        and not _inside(occupied, ws[0][0] + 1, (ly0 + ly1) / 2)):
                    key = f"{pno}:{round(ly0)}:{clabel}"
                    if key not in seen:
                        seen.add(key)
                        fields.append(FormField(
                            name=f"flat_{pno}_{len(fields)}", label=clabel,
                            field_type=FieldType.TEXT, page=pno,
                            bbox=BBox(x0=cw[2] + 4, y0=ly0, x1=sx1, y1=ly1)))
                    continue

            cluster = [ws[0]]
            for prev, cur in zip(ws, ws[1:]):
                if cur[0] - prev[2] <= _LABEL_JOIN_GAP:
                    cluster.append(cur)
                else:
                    break
            raw_label = " ".join(w[4] for w in cluster)
            label = _clean(raw_label)
            if not _looks_like_label(label) or len(cluster) > _MAX_LABEL_WORDS:
                continue

            x0 = cluster[0][0]
            label_end = cluster[-1][2]
            y0 = min(w[1] for w in cluster)
            y1 = max(w[3] for w in cluster)

            if _inside(occupied, x0 + 1, (y0 + y1) / 2):  # 표 안 텍스트는 표 로직이 처리
                continue

            # 1순위: 우측 밑줄 → 인라인 (위치 무관, 밑줄이 필드를 확정)
            cand = [ln for ln in hlines
                    if ln[1] > label_end + 10 and y0 - 4 <= ln[2] <= y1 + 12]
            if cand:
                ln = min(cand, key=lambda l: abs(l[2] - y1))
                bx0, bx1, by0, by1 = ln[0] + 3, ln[1] - 3, ln[2] - 16, ln[2] - 1
            else:
                if x0 > left_zone:
                    continue
                size, bold = font_meta_at(x0 + 1, (y0 + y1) / 2)
                if size >= 18:           # 큰 제목 → 통째로 제외
                    continue
                # 제목/소제목: 머리기호 / 굵은 글씨 / 큰 글씨 → 옆에는 채우지 않음
                heading = _is_heading(raw_label) or bold or size >= 13
                # 2순위: 제목 아래 빈 영역 → 섹션 (문단)
                nt = next_text_top(x0, right, y1)
                gap = (nt - y1) if nt is not None else _SECTION_MAX_H
                if gap >= _SECTION_MIN_GAP:
                    h = min(gap - 6, _SECTION_MAX_H)
                    bx0, bx1, by0, by1 = x0 + 2, right, y1 + 4, y1 + 4 + h
                elif heading:
                    continue  # 제목인데 아래 빈 공간 없음 → 옆에 채우지 않고 건너뜀
                else:
                    # 3순위: 우측 빈 공간 → 인라인 (제목이 아닌 경우만)
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
