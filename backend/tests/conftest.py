"""테스트 공통 설정 — 단위 테스트는 원격 DB에 연결하지 않는다(오프라인·결정론)."""
import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def _disable_db():
    """모든 테스트에서 DB 영속화 비활성화 (db.enabled() → False)."""
    old = settings.db_url
    settings.db_url = ""
    yield
    settings.db_url = old
