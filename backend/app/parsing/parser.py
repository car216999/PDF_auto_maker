"""PDF 파싱·폼필드 추출 — 담당: 채요한.

PyMuPDF(fitz) 로 AcroForm 위젯을 순회하며 필드명·타입·좌표·필수여부·최대길이를
추출하고, 라벨은 위젯 주변 텍스트로 추론한다(좌측 우선, 없으면 상단).

비-AcroForm(평면) PDF 는 위젯이 0개 → 빈 fields + is_form=False 로 안전 처리한다.
(평면 PDF 좌표 오버레이 주입은 중장기 항목)
"""
from pathlib import Path

import fitz  # PyMuPDF

from app.schemas.form import BBox, FieldType, FormField, FormSchema

# fitz 위젯 타입 → 우리 FieldType
_TYPE_MAP = {
    fitz.PDF_WIDGET_TYPE_TEXT: FieldType.TEXT,
    fitz.PDF_WIDGET_TYPE_CHECKBOX: FieldType.CHECKBOX,
    fitz.PDF_WIDGET_TYPE_RADIOBUTTON: FieldType.RADIO,
    fitz.PDF_WIDGET_TYPE_COMBOBOX: FieldType.CHOICE,
    fitz.PDF_WIDGET_TYPE_LISTBOX: FieldType.CHOICE,
    fitz.PDF_WIDGET_TYPE_SIGNATURE: FieldType.SIGNATURE,
}

# AcroForm 필드 플래그: Required = 비트2 (1<<1)
_FLAG_REQUIRED = 1 << 1

# 라벨 추론: 같은 행에서 이 간격(pt)보다 멀면 다른 열로 간주해 끊음
_LABEL_GAP = 28.0


def _clean_label(text: str) -> str:
    """라벨 후처리: 양끝 공백·구분기호 제거."""
    return text.strip().rstrip(":：·").strip()


def _find_label(words: list, rect: fitz.Rect, fallback: str) -> str:
    """위젯 rect 주변 텍스트로 라벨 추론.

    words: page.get_text("words") 결과 — (x0,y0,x1,y1, word, block, line, wno)
    1순위: 같은 행에서 위젯 '왼쪽'에 있는 단어들
    2순위: 위젯 바로 '위'의 가장 가까운 행
    실패 시 fallback(필드명) 반환.
    """
    vcenter = (rect.y0 + rect.y1) / 2
    row_height = max(rect.y1 - rect.y0, 8)

    # --- 1순위: 좌측 같은 행, 필드에 가장 가까운 단어 묶음만 ---
    # (다열 양식에서 다른 열 라벨까지 끌어오지 않도록 큰 간격에서 끊는다)
    left = [
        (x0, x1, w)
        for (x0, y0, x1, y1, w, *_) in words
        if x1 <= rect.x0 + 2 and abs((y0 + y1) / 2 - vcenter) <= row_height
    ]
    if left:
        left.sort(key=lambda t: t[0])
        cluster = [left[-1]]  # 필드에 가장 가까운(오른쪽) 단어부터
        for x0, x1, w in reversed(left[:-1]):
            if cluster[0][0] - x1 <= _LABEL_GAP:  # 간격이 작으면 같은 라벨 구절
                cluster.insert(0, (x0, x1, w))
            else:
                break  # 큰 간격 → 다른 열의 라벨이므로 중단
        label = _clean_label(" ".join(w for _, _, w in cluster))
        if label:
            return label

    # --- 2순위: 상단 가장 가까운 행 ---
    above = [
        (rect.y0 - y1, x0, w)
        for (x0, y0, x1, y1, w, *_) in words
        if y1 <= rect.y0 + 2 and not (x1 < rect.x0 - 2 or x0 > rect.x1 + 2)
    ]
    if above:
        above.sort()
        nearest_dy = above[0][0]
        row = sorted((x0, w) for dy, x0, w in above if abs(dy - nearest_dy) < 3)
        label = _clean_label(" ".join(w for _, w in row))
        if label:
            return label

    return fallback


def _widget_options(widget) -> list[str]:
    """choice 계열 위젯의 선택지."""
    vals = getattr(widget, "choice_values", None)
    if not vals:
        return []
    out = []
    for v in vals:
        # choice_values 항목은 문자열이거나 (export, display) 튜플일 수 있음
        out.append(v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else str(v))
    return out


class PDFParser:
    def parse(self, pdf_path: Path, form_id: str) -> FormSchema:
        """빈 양식 PDF → 정형화된 FormSchema."""
        doc = fitz.open(pdf_path)
        try:
            fields: list[FormField] = []
            seen: set[str] = set()

            for pno, page in enumerate(doc):
                words = page.get_text("words")
                for widget in (page.widgets() or []):
                    field = self._field_from_widget(widget, words, pno)
                    if field is None:
                        continue
                    # 라디오 등 동일 필드명 위젯 중복 → 첫 항목만
                    if field.name in seen:
                        continue
                    seen.add(field.name)
                    fields.append(field)

            return FormSchema(
                form_id=form_id,
                filename=pdf_path.name,
                page_count=doc.page_count,
                fields=fields,
                metadata={
                    "is_form": bool(doc.is_form_pdf),
                    "widget_count": len(fields),
                    "title": doc.metadata.get("title", "") if doc.metadata else "",
                },
            )
        finally:
            doc.close()

    def _field_from_widget(self, widget, words: list, pno: int) -> FormField | None:
        try:
            name = (widget.field_name or "").strip()
            if not name:
                return None
            rect = widget.rect
            ftype = _TYPE_MAP.get(widget.field_type, FieldType.UNKNOWN)
            label = _find_label(words, rect, fallback=name)
            flags = getattr(widget, "field_flags", 0) or 0
            maxlen = getattr(widget, "text_maxlen", 0) or 0

            return FormField(
                name=name,
                label=label,
                field_type=ftype,
                page=pno,
                bbox=BBox(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1),
                required=bool(flags & _FLAG_REQUIRED),
                options=_widget_options(widget),
                max_length=maxlen if maxlen > 0 else None,
            )
        except Exception:
            # 위젯 하나가 깨져도 전체 파싱은 계속
            return None
