from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[3]


def test_initial_migration_enforces_unique_client_order_id() -> None:
    versions = BACKEND_ROOT / "alembic" / "versions"
    files = list(versions.glob("*phase1_initial*.py"))
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    assert 'sa.UniqueConstraint("client_order_id", name="uq_orders_client_order_id")' in text
    assert "sa.Numeric()" in text
    assert "sa.Float" not in text

    script = ScriptDirectory.from_config(Config(str(BACKEND_ROOT / "alembic.ini")))
    assert script.get_heads() == ["d587f5e75b76"]
    assert script.get_base() == "d587f5e75b76"
