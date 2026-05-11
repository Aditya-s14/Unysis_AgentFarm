"""Strict DB verifier — fails loudly on missing tables, bad counts, or query errors.

This script does *not* run ``init_db``/``seed_if_empty`` itself. It exists to
prove what is actually in Postgres after the FastAPI lifespan has run.
Exits non-zero on any failure (missing relation, wrong count, connection error,
or unexpected exception). Every check prints either ``PASS`` or ``FAIL`` on
its own line so CI / docker logs are unambiguous.
"""

from __future__ import annotations

import asyncio
import sys
import traceback
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import get_settings


EXPECTED_TABLES: tuple[str, ...] = (
    "farms",
    "demand_points",
    "trucks",
    "plans",
    "run_logs",
    "plan_outcomes",
)

EXPECTED_COUNTS: dict[str, int] = {
    "farms": 20,
    "demand_points": 10,
    "trucks": 10,
    "plans": 40,
    "plan_outcomes": 40,
}


async def _list_relations(conn) -> set[str]:
    rows = await conn.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        ),
    )
    return {r[0] for r in rows.fetchall()}


async def _count(conn, table: str) -> int:
    result = await conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
    value = result.scalar()
    if value is None:
        raise RuntimeError(f"COUNT(*) on {table!r} returned NULL")
    return int(value)


async def main() -> int:
    settings = get_settings()
    print(f"[verify_db] DATABASE_URL={settings.DATABASE_URL}")

    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    failures: list[str] = []

    try:
        async with engine.connect() as conn:
            relations = await _list_relations(conn)

            for table in EXPECTED_TABLES:
                if table in relations:
                    print(f"PASS  table-exists  {table}")
                else:
                    msg = f"FAIL  table-missing {table}"
                    print(msg)
                    failures.append(msg)

            for table, expected in EXPECTED_COUNTS.items():
                if table not in relations:
                    msg = f"FAIL  count-skipped {table} (table missing)"
                    print(msg)
                    failures.append(msg)
                    continue
                actual = await _count(conn, table)
                if actual == expected:
                    print(f"PASS  count          {table:<14} expected={expected:<4} actual={actual}")
                else:
                    msg = (
                        f"FAIL  count          {table:<14} expected={expected:<4} actual={actual}"
                    )
                    print(msg)
                    failures.append(msg)
    except Exception:
        print("FAIL  unexpected-exception during verification:")
        traceback.print_exc()
        await engine.dispose()
        return 2
    finally:
        await engine.dispose()

    if failures:
        print(f"\nverify_db: FAILED — {len(failures)} check(s) did not pass")
        return 1

    print("\nverify_db: OK — all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
