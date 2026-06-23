"""평면(비-AcroForm) PDF 필드 감지 — 라벨 + 빈 공간 패턴.

입력 위젯이 없는 PDF에서 '짧은 라벨 텍스트 + 오른쪽 빈 공간(밑줄 등)' 패턴을 찾아
채울 가짜 필드(라벨 + 좌표)를 만든다. 양식형 평면 PDF에 적합.
(가이드/서술형 문서에서는 오탐이 있을 수 있어 보수적으로 필터링)
"""
import re

import fitz

from app.schemas.form import BBox, FieldType, FormField

_LABEL_JOIN_GAP = 14.0   # 라벨 내 단어 결합 허용 간격(pt)
_MIN_SLOT_W = 80.0       # 빈칸으로 인정할 최소 폭(pt)
_MAX_LABEL_LEN = 14      # 라벨 최대 글자수
_MAX_LABEL_WORDS = 4
_RIGHT_MARGIN = 45.0     # 페이지 우측 여백


def _clean(text: str) -> str:
    return text.strip().rstrip(":：·").strip()


def _looks_like_label(text: str) -> bool:
    if not (2 <= len(text) <= _MAX_LABEL_LEN):
        return False
    if text.endswith((".", ",", "다", "음", "함")):  # 문장형 제외
        return False
    if re.fullmatch(r"[\d\s.,\-/]+", text):  # 숫자/기호만 제외
        return False
    return True


def _horizontal_lines(page: fitz.Page) -> list[tuple[float, float, float]]:
    """페이지의 수평선(밑줄) 목록 → (x0, x1, y)."""
    out: list[tuple[float, float, float]] = []
    for dr in page.get_drawings():
        for it in dr["items"]:
            if it[0] == "l":  # 선분
                p1, p2 = it[1], it[2]
                if abs(p1.y - p2.y) < 1.5 and abs(p2.x - p1.x) >= _MIN_SLOT_W:
                    out.append((min(p1.x, p2.x), max(p1.x, p2.x), (p1.y + p2.y) / 2))
            elif it[0] == "re":  # 얇은 사각형도 밑줄로 취급
                r = it[1]
                if r.height < 2 and r.width >= _MIN_SLOT_W:
                    out.append((r.x0, r.x1, (r.y0 + r.y1) / 2))
    return out


def detect_flat_fields(doc: fitz.Document) -> list[FormField]:
    fields: list[FormField] = []
    seen: set[str] = set()

    for pno, page in enumerate(doc):
        right = page.rect.width - _RIGHT_MARGIN
        hlines = _horizontal_lines(page)
        words = page.get_text("words")  # (x0,y0,x1,y1, word, block, line, wno)
        lines: dict[tuple, list] = {}
        for w in words:
            lines.setdefault((w[5], w[6]), []).append(w)

        left_zone = page.rect.width * 0.4  # 라벨은 좌측 영역에 있어야 함(가운데 정렬 제목 제외)
        for ws in lines.values():
            ws.sort(key=lambda w: w[0])
            if ws[0][0] > left_zone:  # 좌측에서 시작하지 않으면 라벨 아님(제목 등)
                continue
            # 왼쪽부터 간격 작은 단어들 = 라벨 클러스터
            cluster = [ws[0]]
            for prev, cur in zip(ws, ws[1:]):
                if cur[0] - prev[2] <= _LABEL_JOIN_GAP:
                    cluster.append(cur)
                else:
                    break
            label = _clean(" ".join(w[4] for w in cluster))
            if not _looks_like_label(label) or len(cluster) > _MAX_LABEL_WORDS:
                continue

            label_end = cluster[-1][2]
            y0 = min(w[1] for w in cluster)
            y1 = max(w[3] for w in cluster)

            # 1순위: 라벨 우측의 밑줄에 정렬 (밑줄 위에 값을 얹음)
            cand = [ln for ln in hlines
                    if ln[1] > label_end + 10 and y0 - 4 <= ln[2] <= y1 + 12]
            if cand:
                ln = min(cand, key=lambda l: abs(l[2] - y1))  # 베이스라인에 가장 가까운 선
                slot_left = ln[0] + 3
                slot_right = ln[1] - 3
                y0, y1 = ln[2] - 16, ln[2] - 1     # 선 바로 위
            else:
                # 2순위: 라벨 우측 빈 공간(밑줄 없음)
                rest = [w for w in ws if w[0] > label_end + 1]
                slot_left = label_end + 8
                slot_right = (rest[0][0] - 4) if rest else right
            if slot_right - slot_left < _MIN_SLOT_W:  # 빈칸 부족
                continue
            key = f"{pno}:{round(y0)}:{label}"
            if key in seen:
                continue
            seen.add(key)
            fields.append(FormField(
                name=f"flat_{pno}_{len(fields)}",
                label=label,
                field_type=FieldType.TEXT,
                page=pno,
                bbox=BBox(x0=slot_left, y0=y0, x1=slot_right, y1=y1),
            ))

    return fields
