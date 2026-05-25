import asyncio
import logging
import sys
from newsdash.db.models import create_db_engine, get_session_factory
from newsdash.digest.mailer import send_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

async def main():
    print("Initiating real email dispatch now...")
    engine = create_db_engine()
    session_factory = get_session_factory(engine)
    async with session_factory() as session:
        try:
            await send_digest(session)
            print("\nEmail dispatch task completed successfully.")
        except Exception as e:
            print(f"\nError during email dispatch: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
