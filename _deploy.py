"""Deploy script: run migrations and seed all JSON data into the target database."""
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


async def main():
    from app.database.connection import create_pool
    from app.database.migrations import run_migrations, seed_from_json
    from app.core.config import get_settings

    settings = get_settings()
    print(f"Target: {settings.database_url}")
    print(f"IAM auth: {settings.rds_iam_auth}  Region: {settings.aws_region}")
    print()

    pool = await create_pool(settings.database_url)
    await run_migrations(pool)
    await seed_from_json(pool, settings.data_dir)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT context, COUNT(*) AS cnt
            FROM   knowledge_chunks
            WHERE  user_id IS NULL
            GROUP BY context
            ORDER BY context
            """
        )
        print()
        print("=== Chunks in cloud DB ===")
        total = 0
        for r in rows:
            print(f"  {r['context']:<20}  {r['cnt']:>3} chunks")
            total += r["cnt"]
        print(f"  {'TOTAL':<20}  {total:>3} chunks")

    await pool.close()
    print()
    print("Deploy complete.")


asyncio.run(main())
