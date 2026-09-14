"""In-process BM25 index over stored chunks, used alongside vector search.

Pure Python, no dependencies. The index is rebuilt lazily when the chunk table changes.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Chunk

K1 = 1.5
B = 0.75

STOPWORDS = frozenset(
    """a about above after again against all am an and any are as at be because been before being
    below between both but by can could did do does doing down during each few for from further had
    has have having he her here hers herself him himself his how i if in into is it its itself just
    me more most my myself no nor not now of off on once only or other our ours ourselves out over own
    same she should so some such than that the their theirs them themselves then there these they this
    those through to too under until up very was we were what when where which while who whom why will
    with would you your yours yourself yourselves""".split()
)

_TOKEN = re.compile(r"[a-z0-9]+")


def _stem(token: str) -> str:
    """Tiny plural folding; enough to match 'folds'/'fold' without a stemming dependency."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    return [_stem(t) for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]


@dataclass
class _Posting:
    chunk_index: int
    tf: int


class BM25Index:
    def __init__(self, entries: list[tuple[str, str, str]]):
        """entries: (chunk_id, document_id, text)."""
        self.chunk_ids = [cid for cid, _, _ in entries]
        self.document_ids = [did for _, did, _ in entries]
        self.lengths: list[int] = []
        self.postings: dict[str, list[_Posting]] = defaultdict(list)
        for i, (_, _, text) in enumerate(entries):
            counts = Counter(tokenize(text))
            self.lengths.append(sum(counts.values()))
            for term, tf in counts.items():
                self.postings[term].append(_Posting(i, tf))
        self.n = len(entries)
        self.avg_len = (sum(self.lengths) / self.n) if self.n else 0.0

    def idf(self, term: str) -> float:
        df = len(self.postings.get(term, ()))
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, query: str, limit: int, document_ids: list[str] | None = None) -> list[tuple[str, float, float]]:
        """Returns (chunk_id, bm25_score, query_coverage) sorted by score.

        query_coverage in [0, 1] is the chunk's BM25 score divided by the score upper bound
        (every query term matched with saturated frequency), i.e. how much of the query's
        IDF-weighted vocabulary the chunk contains. It is comparable across queries.
        """
        terms = set(tokenize(query))
        if not terms or not self.n:
            return []
        allowed = set(document_ids) if document_ids else None
        upper_bound = sum(self.idf(t) * (K1 + 1) for t in terms)
        scores: dict[int, float] = defaultdict(float)
        for term in terms:
            idf = self.idf(term)
            for posting in self.postings.get(term, ()):
                if allowed is not None and self.document_ids[posting.chunk_index] not in allowed:
                    continue
                norm = K1 * (1 - B + B * self.lengths[posting.chunk_index] / self.avg_len)
                scores[posting.chunk_index] += idf * posting.tf * (K1 + 1) / (posting.tf + norm)
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
        return [
            (self.chunk_ids[i], score, min(1.0, score / upper_bound) if upper_bound > 0 else 0.0)
            for i, score in ranked
        ]


_cache: dict[str, tuple[tuple[int, int], BM25Index]] = {}


async def get_bm25_index(db: AsyncSession) -> BM25Index:
    """Returns a cached index, rebuilding it when chunk count or total text length changes."""
    count, total_len = (await db.execute(select(func.count(Chunk.id), func.coalesce(func.sum(func.length(Chunk.text)), 0)))).one()
    signature = (int(count), int(total_len))
    key = str(db.bind.url) if db.bind is not None else "default"
    cached = _cache.get(key)
    if cached and cached[0] == signature:
        return cached[1]
    rows = (await db.execute(select(Chunk.id, Chunk.document_id, Chunk.text))).all()
    index = BM25Index([(r.id, r.document_id, r.text) for r in rows])
    _cache[key] = (signature, index)
    return index
