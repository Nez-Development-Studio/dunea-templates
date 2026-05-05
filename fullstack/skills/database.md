# database — MongoDB CRUD, Lists, and Multi-Tenant Queries

## When to use

Pull this skill in when the task involves: listing records (dashboards, feeds,
tables), reading or updating a single record by ID, filtering records by the
current user ("show me only MY posts"), pagination, sorting, or anything that
returns more than one document. Simple single-form-to-collection cases (like a
contact form) are already covered by `BASE.md` — use that; don't pull this
skill in for them.

## Primitive

All DB access goes through the pre-initialized `db` object in `backend/database.py`.
Two helpers live there alongside it that every CRUD route should use:

```python
from database import db, serialize_doc, serialize_docs
```

- `db.<collection>.find(...)`, `.insert_one(...)`, `.update_one(...)`, etc. — plain PyMongo, synchronous.
- `serialize_doc(doc)` — one doc → JSON-safe dict with `id` instead of `_id`. Returns None if input is None.
- `serialize_docs(cursor)` — iterable of docs → list of JSON-safe dicts. Use this on every `find()` result before returning.

No ORM, no async, no Beanie. Plain PyMongo + the two helpers.

## Backend example

Full CRUD router for a "posts" resource owned by the currently-logged-in user.
Copy this shape and rename for any user-scoped resource (todos, projects,
comments, bookmarks, etc.).

```python
# backend/routes/posts.py
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from bson import ObjectId
from bson.errors import InvalidId

from database import db, serialize_doc, serialize_docs
from routes.auth import require_login  # only if the auth skill is in play

router = APIRouter()


# ---- Pydantic models ----
# SEPARATE the request shape from the document shape. Never reuse one
# BaseModel for both input and output — they have different fields.

class PostCreate(BaseModel):
    title: str
    body: str


class PostUpdate(BaseModel):
    title: str | None = None
    body: str | None = None


class PostPublic(BaseModel):
    id: str
    user_id: str
    title: str
    body: str
    created_at: datetime
    updated_at: datetime


# ---- Helpers ----

def _parse_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Not found")


# ---- Routes ----

@router.post("", response_model=PostPublic)
async def create_post(data: PostCreate, user: dict = Depends(require_login)):
    now = datetime.now(timezone.utc)
    doc = {
        **data.model_dump(),
        "user_id": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    result = db.posts.insert_one(doc)
    return serialize_doc(db.posts.find_one({"_id": result.inserted_id}))


@router.get("")
async def list_posts(
    user: dict = Depends(require_login),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    filter_ = {"user_id": user["id"]}
    cursor = (
        db.posts.find(filter_)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    total = db.posts.count_documents(filter_)
    return {"items": serialize_docs(cursor), "total": total, "skip": skip, "limit": limit}


@router.get("/{post_id}", response_model=PostPublic)
async def get_post(post_id: str, user: dict = Depends(require_login)):
    post = db.posts.find_one({"_id": _parse_object_id(post_id), "user_id": user["id"]})
    if not post:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_doc(post)


@router.patch("/{post_id}", response_model=PostPublic)
async def update_post(post_id: str, data: PostUpdate, user: dict = Depends(require_login)):
    updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc)

    result = db.posts.update_one(
        {"_id": _parse_object_id(post_id), "user_id": user["id"]},
        {"$set": updates},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_doc(db.posts.find_one({"_id": _parse_object_id(post_id)}))


@router.delete("/{post_id}")
async def delete_post(post_id: str, user: dict = Depends(require_login)):
    result = db.posts.delete_one(
        {"_id": _parse_object_id(post_id), "user_id": user["id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"success": True}
```

Register the router in `backend/main.py`:

```python
from routes.posts import router as posts_router
app.include_router(posts_router, prefix="/api/posts")
```

## Indexes

For any collection where you filter by `user_id`, sort by `created_at`, or
look up by a secondary field (email, slug, etc.), create an index at app
startup. Add this to `backend/main.py` once, below the router registrations:

```python
from database import db

@app.on_event("startup")
async def create_indexes():
    db.posts.create_index([("user_id", 1), ("created_at", -1)])
    db.posts.create_index("user_id")
    # Add one line per index each collection needs.
```

Index creation is idempotent — safe to call on every startup. Without them,
your list endpoints will fall over at a few thousand documents.

## Frontend example

Standard pattern for calling a user-scoped list endpoint with the auth token
already attached. Reuses the `authHeaders()` helper from the auth skill if it
exists; otherwise inline the `Authorization: Bearer` header.

```tsx
// frontend/src/lib/posts.ts
import { authHeaders } from '@/lib/auth';

export type Post = {
  id: string;
  user_id: string;
  title: string;
  body: string;
  created_at: string;
  updated_at: string;
};

type ListResponse = { items: Post[]; total: number; skip: number; limit: number };

export async function listPosts(skip = 0, limit = 20): Promise<ListResponse> {
  const res = await fetch(`/api/posts?skip=${skip}&limit=${limit}`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Failed to load');
  return res.json();
}

export async function createPost(title: string, body: string): Promise<Post> {
  const res = await fetch('/api/posts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ title, body }),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Failed to create');
  return res.json();
}

export async function deletePost(id: string): Promise<void> {
  const res = await fetch(`/api/posts/${id}`, {
    method: 'DELETE',
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Failed to delete');
}
```

Consume it in a component with the shadcn Table pattern (or any list UI):

```tsx
// frontend/src/pages/Posts.tsx
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { listPosts, type Post } from '@/lib/posts';

export default function PostsPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listPosts()
      .then((res) => setPosts(res.items))
      .catch((err) => toast.error(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6">Loading…</div>;
  if (posts.length === 0) return <div className="p-6">No posts yet.</div>;

  return (
    <ul className="space-y-4 p-6">
      {posts.map((p) => (
        <li key={p.id} className="rounded-lg border p-4">
          <h3 className="font-semibold">{p.title}</h3>
          <p className="text-sm text-muted-foreground">{p.body}</p>
        </li>
      ))}
    </ul>
  );
}
```

## Env vars

None — MongoDB URL is already loaded from `backend/.env` by `database.py` via
pydantic-settings. Never hardcode the connection string.

## Gotchas

1. **Don't use one Pydantic model for both request body and stored document.**
   The request shape is what the client sends (`PostCreate`: title, body). The
   stored shape is what lives in Mongo (`user_id`, `created_at`, `_id`). The
   response shape is what the client sees (`PostPublic`: id as string, no
   ObjectId). Separating them is the difference between a clean API and a
   leaky one.

2. **Always `$set` on updates.** `db.col.update_one({"_id": id}, {"title": "x"})`
   is **wrong** — that replaces the entire document with `{"title": "x"}`,
   destroying every other field. The correct form is
   `db.col.update_one({"_id": id}, {"$set": {"title": "x"}})`. Every single
   update. No exceptions.

3. **Always convert string IDs with `ObjectId(id_str)` before querying.** The
   client sends `"67f1a2b3c4d5e6f7a8b9c0d1"` as a string; Mongo stores `_id`
   as an `ObjectId`. A query like `db.posts.find_one({"_id": post_id})` with
   `post_id` as a raw string will silently return `None`. Use the
   `_parse_object_id` helper shown above — it also returns a clean 404 on
   malformed IDs instead of a 500.

4. **Never return a raw PyMongo cursor.** `return db.posts.find(...)` sends
   an unserializable object to FastAPI and you get a 500. Always wrap in
   `serialize_docs(cursor)`.

5. **Filter every user-scoped query by `user_id`.** For any resource a user
   owns (posts, todos, projects, files), every `find`, `update_one`,
   `delete_one` MUST include `"user_id": user["id"]` in the filter. Forgetting
   this is a multi-tenant data leak — user A can read/update/delete user B's
   records by guessing IDs.

6. **Don't serialize the `password_hash` field.** If you ever store a user
   document and return it via `serialize_doc`, make sure you explicitly
   exclude `password_hash` (and any other secret field) before returning.
   `serialize_doc` does NOT filter — it's not its job. Build a
   `public_user(doc)` helper that picks only the safe fields (see the auth
   skill for the canonical example).

7. **`find_one` returns `None` if nothing matches — check before indexing.**
   `doc = db.posts.find_one({"_id": id}); return doc["title"]` crashes with a
   `TypeError` when the post doesn't exist. Always check `if not doc:` and
   raise a 404.

8. **Create indexes at startup.** Without them, a list endpoint on 10K
   documents spends seconds per request doing full collection scans. The
   `@app.on_event("startup")` hook shown above is the one place you should
   call `create_index`. Never inside a route handler.
