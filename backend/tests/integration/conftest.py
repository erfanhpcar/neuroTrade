from collections.abc import Iterator

import pytest

from tests.integration.db_support import require_postgres, reset_public_schema, run_upgrade


@pytest.fixture
def migrated_database_url() -> Iterator[str]:
    import asyncio

    url = require_postgres()
    asyncio.run(reset_public_schema(url))
    run_upgrade(url)
    yield url
