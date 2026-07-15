"""Database migration script."""
import asyncio
from .connection import engine, init_db


async def migrate():
    """Run database migrations."""
    print("Running database migrations...")
    await init_db()
    print("Migrations complete!")


if __name__ == "__main__":
    asyncio.run(migrate())