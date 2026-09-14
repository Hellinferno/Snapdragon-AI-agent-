#!/usr/bin/env python3
"""Re-embeds every indexed chunk with the currently configured embedding provider.

Use after changing EMBEDDING_PROVIDER (e.g. to onnx_minilm). Documents, pages and chunks are
kept; only vectors are replaced. Run from backend/:  python scripts/reindex_embeddings.py
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory, init_db  # noqa: E402
from app.providers.factory import get_embedding_provider  # noqa: E402
from app.services.embedding_index import get_index_provider, reembed_all_chunks  # noqa: E402


async def main() -> None:
    await init_db()
    provider = get_embedding_provider()
    async with async_session_factory() as db:
        before = await get_index_provider(db)
        t0 = time.perf_counter()
        count = await reembed_all_chunks(db, provider)
    print(f"Re-embedded {count} chunks: {before} -> {provider.name} in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
