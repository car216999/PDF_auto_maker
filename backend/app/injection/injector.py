"""PDF 주입 — 담당: 이권형 / 채요한.

채워진 값을 원본 빈 PDF 의 필드 좌표에 한글로 주입하고 평탄화(flatten)한다.

[한글 폰트 전략]
  AcroForm 위젯 appearance 에 직접 한글을 넣으면 폰트 미임베딩으로 글자가 깨지기 쉽다
  (reportlab 등이 Helvetica DA 로 양식 생성). 그래서 파싱에서 추출한 위젯 좌표에
  PyMuPDF 내장 한국어 폰트로 텍스트를 오버레이한 뒤 위젯을 평탄화한다.
  → 외부 폰트 파일 의존 없이 한글이 확실히 렌더링되고, '좌표 정밀 주입'을 실현한다.
  (중장기: 평면 비-AcroForm PDF 도 동일 좌표 오버레이로 확장 가능)
"""
from pathlib import Path

import fitz  # PyMuPDF

from app.schemas.generation import FilledField

# 체크박스를 '켬'으로 해석할 값
_TRUTHY = {"y", "yes", "true", "1", "예", "o", "on", "check", "checked", "v", "✓"}


class PDFInjector:
    def __init__(
        self,
        flatten: bool = True,
        font_size: int = 11,
        fontname: str = "korea",  # PyMuPDF 내장 한국어 폰트
        fontfile: str | None = None,  # 사용자 지정 TTF(예: malgun.ttf) 시 우선
    ):
        self.flatten = flatten
        self.font_size = font_size
        self.fontname = "kfont" if fontfile else fontname
        self.fontfile = fontfile

    def fill(self, src_pdf: Path, fields: list[FilledField], out_pdf: Path) -> Path:
        """원본 빈 PDF + 값 → 채워진 PDF."""
        values = {f.name: (f.value or "").strip() for f in fields}
        doc = fitz.open(src_pdf)
        try:
            overlays: list[tuple[int, fitz.Rect, str, bool]] = []  # (page, rect, text, is_check)

            for pno, page in enumerate(doc):
                for widget in list(page.widgets() or []):
                    name = widget.field_name
                    if name not in values:
                        continue
                    val = values[name]
                    rect = widget.rect
                    is_checkbox = widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX

                    if self.flatten:
                        # 평탄화 모드: 위젯 appearance 대신 좌표 오버레이로 그린다
                        if is_checkbox:
                            if val.lower() in _TRUTHY:
                                overlays.append((pno, rect, "X", True))
                        elif val:
                            overlays.append((pno, rect, val, False))
                    else:
                        # 대화형 유지 모드: 위젯 값에 직접 기입 (데이터 보존)
                        self._set_widget_value(widget, val, is_checkbox)

            if self.flatten:
                doc.bake(widgets=True)  # 위젯 → 정적 콘텐츠 (테두리 유지, 편집 불가)
                for pno, rect, text, is_check in overlays:
                    self._draw(doc[pno], rect, text, is_check)

            out_pdf.parent.mkdir(parents=True, exist_ok=True)
            doc.save(out_pdf, garbage=3, deflate=True)
        finally:
            doc.close()
        return out_pdf

    def _draw(self, page, rect: fitz.Rect, text: str, is_check: bool) -> None:
        """필드 좌표에 한글 텍스트(또는 체크표시)를 오버레이.

        긴 값은 필드 폭에 맞게 글자 크기를 자동 축소해 잘리거나 사라지지 않게 한다.
        insert_text(점 기준)는 박스 클리핑이 없어 항상 렌더링된다.
        """
        if is_check:
            size = self.font_size
            x = rect.x0 + rect.width / 2 - size * 0.3
            page.insert_text((x, rect.y1 - 5), "X", fontname=self.fontname,
                             fontfile=self.fontfile, fontsize=size)
            return

        # 키 큰 필드(멀티라인 문단)는 줄바꿈되는 textbox 로 렌더링
        if (rect.y1 - rect.y0) > 34:
            self._draw_paragraph(page, rect, text)
            return

        # 단일행: 폭에 맞게 글자 크기 자동 축소
        box_w = max(rect.x1 - rect.x0 - 4, 1.0)
        # 내장 CJK 폰트는 영문도 전각으로 그리므로 모든 글자를 ~1em 으로 보수 추정
        units = float(max(len(text), 1))
        size = max(6.0, min(float(self.font_size), box_w / units))
        baseline = rect.y1 - max(4.0, (rect.y1 - rect.y0 - size) / 2)
        page.insert_text((rect.x0 + 2, baseline), text, fontname=self.fontname,
                         fontfile=self.fontfile, fontsize=size)

    def _draw_paragraph(self, page, rect: fitz.Rect, text: str) -> None:
        """멀티라인 박스: 박스 용량에 맞게 글자 크기를 미리 추정해 한 번에 그린다."""
        box = fitz.Rect(rect.x0 + 3, rect.y0 + 2, rect.x1 - 3, rect.y1 - 2)
        box_w, box_h = box.width, box.height
        n = max(len(text), 1)
        size = float(self.font_size)
        while size > 6:
            chars_per_line = max(box_w / (size * 0.95), 1)  # 한글 기준 보수적
            lines = box_h / (size * 1.3)
            if chars_per_line * lines >= n * 1.15:  # 15% 여유
                break
            size -= 0.5
        page.insert_textbox(box, text, fontname=self.fontname, fontfile=self.fontfile,
                            fontsize=size, align=fitz.TEXT_ALIGN_LEFT)

    @staticmethod
    def _set_widget_value(widget, val: str, is_checkbox: bool) -> None:
        try:
            if is_checkbox:
                widget.field_value = val.lower() in _TRUTHY
            else:
                widget.field_value = val
            widget.update()
        except Exception:
            pass  # 위젯 하나 실패가 전체를 막지 않도록
