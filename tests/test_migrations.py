import pytest

from ..migrations import m013_make_lnaddress_usernames_unique


class MigrationDatabase:
    def __init__(self, duplicate=None):
        self.duplicate = duplicate
        self.queries = []

    async def fetchone(self, query):
        self.queries.append(query)
        return self.duplicate

    async def execute(self, query):
        self.queries.append(query)


@pytest.mark.asyncio
async def test_username_uniqueness_migration_adds_case_insensitive_index():
    db = MigrationDatabase()

    await m013_make_lnaddress_usernames_unique(db)

    assert "LOWER(username)" in db.queries[1]


@pytest.mark.asyncio
async def test_username_uniqueness_migration_refuses_legacy_duplicates():
    db = MigrationDatabase(duplicate=("alice",))

    with pytest.raises(RuntimeError, match="duplicate usernames"):
        await m013_make_lnaddress_usernames_unique(db)

    assert len(db.queries) == 1
