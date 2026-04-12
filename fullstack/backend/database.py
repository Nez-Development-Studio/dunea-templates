from typing import Iterable

import certifi
from pymongo import MongoClient

from config import settings

client = MongoClient(settings.MONGODB_URL, tlsCAFile=certifi.where())
db = client[settings.DATABASE_NAME]


def serialize_doc(doc: dict | None) -> dict | None:
    """Convert a MongoDB document for a JSON response.

    Pops the bson ObjectId from `_id` and re-adds it as a string under `id`,
    so clients don't have to know about ObjectId. Returns None if the input
    is None (useful for `find_one` results that may not exist).

    Use in every route that returns a single document.
    """
    if doc is None:
        return None
    out = {**doc}
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    return out


def serialize_docs(cursor: Iterable[dict]) -> list[dict]:
    """Convert a PyMongo cursor (or any iterable of docs) into a JSON-safe list.

    Use in every list endpoint — `.find()` returns a cursor, not a list, and
    FastAPI can't serialize it directly. Drops any None entries defensively.
    """
    return [serialize_doc(d) for d in cursor if d is not None]
