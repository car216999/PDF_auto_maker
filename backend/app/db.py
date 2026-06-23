"""PostgreSQL 영속화 (선택) — settings.db_url 설정 시 폼·문서 이력 저장.

[원칙] DB 미설정/원격 장애 시에도 앱은 메모리로 정상 동작해야 한다.
모든 작업을 try/except 로 감싸 DB 실패가 업로드·생성 흐름을 막지 않게 한다.
(스키마는 DBeaver 로 사전 생성된 9개 테이블을 사용 — 본 모듈은 INSERT/SELECT만)
"""
import logging
import re

from app.config import settings

_PREFIX = re.compile(r"^[0-9a-f]{8}_")  # 업로드 시 붙는 8hex 접두사 제거용


def _clean_name(fn: str) -> str:
    return _PREFIX.sub("", fn or "")

log = logging.getLogger("tooktak.db")
_engine = None
_user_id = None


def enabled() -> bool:
    return bool(settings.db_url)


def _eng():
    global _engine
    if _engine is None:
        from sqlalchemy import create_engine

        _engine = create_engine(
            settings.db_url, pool_pre_ping=True, pool_recycle=300,
            connect_args={"connect_timeout": 8},
        )
    return _engine


def ping() -> bool:
    if not enabled():
        return False
    try:
        from sqlalchemy import text

        with _eng().connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception as e:
        log.warning("DB ping 실패: %s", e)
        return False


def ensure_user():
    global _user_id
    if _user_id is not None:
        return _user_id
    if not enabled():
        return None
    from sqlalchemy import text

    try:
        with _eng().begin() as c:
            row = c.execute(
                text("SELECT user_id FROM users WHERE email=:e"),
                {"e": settings.default_user_email},
            ).first()
            _user_id = row[0] if row else c.execute(
                text("INSERT INTO users(email,name) VALUES(:e,:n) RETURNING user_id"),
                {"e": settings.default_user_email, "n": settings.default_user_name},
            ).scalar()
        return _user_id
    except Exception as e:
        log.warning("ensure_user 실패: %s", e)
        return None


def save_form(schema, src_path: str = "") -> None:
    if not enabled():
        return
    from sqlalchemy import text

    try:
        uid = ensure_user()
        with _eng().begin() as c:
            c.execute(text(
                "INSERT INTO forms(form_id,user_id,filename,page_count,is_form,src_path) "
                "VALUES(:fid,:uid,:fn,:pc,:isf,:sp) ON CONFLICT(form_id) DO NOTHING"),
                {"fid": schema.form_id, "uid": uid, "fn": _clean_name(schema.filename),
                 "pc": schema.page_count,
                 "isf": 1 if schema.metadata.get("is_form") else 0, "sp": str(src_path)})
            c.execute(text("DELETE FROM form_fields WHERE form_id=:fid"),
                      {"fid": schema.form_id})
            for f in schema.fields:
                b = f.bbox
                ft = getattr(f.field_type, "value", str(f.field_type))
                c.execute(text(
                    "INSERT INTO form_fields(form_id,name,label,field_type,page,"
                    "bbox_x0,bbox_y0,bbox_x1,bbox_y1,required,max_length) VALUES "
                    "(:fid,:n,:l,:t,:p,:x0,:y0,:x1,:y1,:rq,:ml)"),
                    {"fid": schema.form_id, "n": f.name, "l": (f.label or "")[:255],
                     "t": str(ft)[:50], "p": f.page,
                     # bbox·max_length 는 NOT NULL → 없으면 0
                     "x0": round(b.x0, 2) if b else 0, "y0": round(b.y0, 2) if b else 0,
                     "x1": round(b.x1, 2) if b else 0, "y1": round(b.y1, 2) if b else 0,
                     "rq": 0, "ml": 0})
    except Exception as e:
        log.warning("save_form 실패: %s", e)


def save_document(form_id: str, concept: str, model: str, fields: list,
                  status: str = "완료") -> None:
    """생성 결과(필드)와 함께 documents + filled_fields 저장. fields: FilledField 목록."""
    if not enabled():
        return
    from sqlalchemy import text

    try:
        uid = ensure_user()
        gr = (sum(1 for f in fields if f.grounded) / len(fields)) if fields else 0.0
        with _eng().begin() as c:
            doc_id = c.execute(text(
                "INSERT INTO documents(form_id,user_id,concept,model,grounded_ratio,"
                "status,output_path) VALUES(:fid,:uid,:con,:mod,:gr,:st,:op) "
                "RETURNING document_id"),
                {"fid": form_id, "uid": uid, "con": concept, "mod": model[:50],
                 "gr": round(gr, 3), "st": status[:20],
                 "op": f"{form_id}_filled.pdf"}).scalar()
            for f in fields:
                c.execute(text(
                    "INSERT INTO filled_fields(document_id,field_name,value,grounded,"
                    "confidence) VALUES(:d,:n,:v,:g,:cf)"),
                    {"d": doc_id, "n": f.name[:100], "v": f.value or "",
                     "g": 1 if f.grounded else 0,
                     "cf": round(float(getattr(f, "confidence", 0) or 0), 3)})
    except Exception as e:
        log.warning("save_document 실패: %s", e)


def recent_documents(limit: int = 8) -> list[dict]:
    if not enabled():
        return []
    from sqlalchemy import text

    try:
        with _eng().connect() as c:
            rows = c.execute(text(
                "SELECT f.filename, d.status, d.created_at, "
                "(SELECT count(*) FROM filled_fields ff WHERE ff.document_id=d.document_id) n "
                "FROM documents d JOIN forms f ON f.form_id=d.form_id "
                "ORDER BY d.created_at DESC LIMIT :lim"), {"lim": limit}).all()
        return [{"name": r[0], "status": r[1],
                 "created_at": r[2].isoformat() if r[2] else "", "fields": r[3]}
                for r in rows]
    except Exception as e:
        log.warning("recent_documents 실패: %s", e)
        return []
