# storage — File Uploads via Presigned URLs

## When to use

Pull this skill in when the task mentions:
- File uploads, image uploads, document uploads
- User avatars, profile pictures
- File hosting, media storage
- Downloading files, serving files to users
- S3, object storage, file storage
- "users can upload", "save files", "store images"

## Primitive

All storage access goes through the pre-initialized helpers in `backend/storage.py`:

```python
from storage import get_upload_url, get_read_url, upload_file, list_files
```

- `get_upload_url(path, content_type)` — returns `{"url": "...", "expiresIn": 900}` for PUT upload
- `get_read_url(path)` — returns a presigned URL string for viewing/downloading
- `upload_file(path, content, content_type)` — convenience: uploads bytes and returns read URL
- `list_files(subpath)` — returns list of `{"key": "...", "size": 123, "lastModified": "..."}`

All functions are async. Storage is only available on deployed apps — in local dev, these raise `RuntimeError`.

## Backend example

Full upload endpoint for user file uploads. Copy this shape for avatars, documents, images, etc.

```python
# backend/routes/uploads.py
from fastapi import APIRouter, UploadFile, HTTPException
from pydantic import BaseModel
import uuid

from storage import upload_file, get_read_url, list_files

router = APIRouter()


class UploadResponse(BaseModel):
    path: str
    url: str


@router.post("/upload", response_model=UploadResponse)
async def upload_user_file(file: UploadFile):
    """Upload a file and return its path + viewable URL."""
    # Generate unique path
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else ""
    path = f"uploads/{uuid.uuid4()}.{ext}" if ext else f"uploads/{uuid.uuid4()}"

    # Read content and upload
    content = await file.read()
    url = await upload_file(path, content, file.content_type or "application/octet-stream")

    return UploadResponse(path=path, url=url)


@router.get("/files/{path:path}")
async def get_file_url(path: str):
    """Get a fresh presigned URL to view/download a file."""
    try:
        url = await get_read_url(path)
        return {"url": url}
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")


@router.get("/files")
async def list_user_files(prefix: str = "uploads/"):
    """List files in a directory."""
    files = await list_files(prefix)
    return {"files": files}
```

Register in `backend/main.py`:

```python
from routes.uploads import router as uploads_router
app.include_router(uploads_router, prefix="/api")
```

## User Avatar Pattern

For user-scoped files (like avatars), include the user ID in the path:

```python
# backend/routes/users.py
from fastapi import APIRouter, UploadFile, Depends
from storage import upload_file, get_read_url
from routes.auth import require_login
from database import db

router = APIRouter()


@router.post("/me/avatar")
async def upload_avatar(file: UploadFile, user: dict = Depends(require_login)):
    """Upload current user's avatar."""
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "png"
    path = f"avatars/{user['id']}.{ext}"

    content = await file.read()
    url = await upload_file(path, content, file.content_type or "image/png")

    # Store path in user document
    db.users.update_one({"_id": user["_id"]}, {"$set": {"avatar_path": path}})

    return {"path": path, "url": url}


@router.get("/me/avatar")
async def get_avatar(user: dict = Depends(require_login)):
    """Get current user's avatar URL."""
    avatar_path = user.get("avatar_path")
    if not avatar_path:
        return {"url": None}

    url = await get_read_url(avatar_path)
    return {"url": url}
```

## Frontend example

Standard file upload component using the backend endpoints:

```tsx
// frontend/src/components/FileUpload.tsx
import { useState } from 'react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

interface UploadResult {
  path: string;
  url: string;
}

export function FileUpload({ onUpload }: { onUpload: (result: UploadResult) => void }) {
  const [uploading, setUploading] = useState(false);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const result = await api('/api/upload', {
        method: 'POST',
        body: formData,
        // Don't set Content-Type — browser sets it with boundary for FormData
      });

      toast.success('File uploaded!');
      onUpload(result as UploadResult);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <input
        type="file"
        onChange={handleFileChange}
        disabled={uploading}
        className="hidden"
        id="file-upload"
      />
      <label htmlFor="file-upload">
        <Button asChild disabled={uploading}>
          <span>{uploading ? 'Uploading...' : 'Choose File'}</span>
        </Button>
      </label>
    </div>
  );
}
```

Display a stored image:

```tsx
// frontend/src/components/StoredImage.tsx
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

export function StoredImage({ path, alt, className }: { path: string; alt: string; className?: string }) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    api(`/api/files/${encodeURIComponent(path)}`)
      .then((data) => setUrl((data as { url: string }).url))
      .catch(() => setUrl(null));
  }, [path]);

  if (!url) return <div className={`animate-pulse bg-gray-200 rounded ${className}`} />;

  return <img src={url} alt={alt} className={className} />;
}
```

## Env vars

None to configure — `DUNEA_STORAGE_API` and `DUNEA_STORAGE_SECRET` are set
automatically by the platform on deployed apps. The `storage.py` module reads
them from `config.py` via pydantic-settings. Never hardcode storage credentials.

## Gotchas

1. **Storage only works on deployed apps.** In local development, the storage
   functions raise `RuntimeError` because the env vars aren't set. Either:
   - Mock the storage functions for local dev
   - Skip storage features during local development
   - Set up a local MinIO instance

2. **Presigned URLs expire.** Read URLs are valid for 1 hour, upload URLs for
   15 minutes. Don't cache them long-term or store them in the database. Always
   fetch fresh URLs when displaying images.

3. **Use FormData for uploads.** When uploading from the frontend, use
   `FormData` and do NOT set `Content-Type` header — the browser sets it
   automatically with the correct multipart boundary.

4. **Path structure matters.** Use meaningful paths like `avatars/{user_id}.png`
   or `uploads/{uuid}/{filename}`. Paths are scoped to your deployment
   automatically — you don't need to add a prefix.

5. **Don't expose raw paths in URLs.** Always fetch a fresh presigned URL
   through your backend. Never expose the raw storage path in URLs that users
   might bookmark — they'll break when the presigned URL expires.

6. **Content-Type must match.** Set the correct `Content-Type` when uploading.
   The presigned URL is scoped to the content type you requested.

7. **File size limits.** FastAPI receives the file first before uploading to
   storage. For very large files (>50MB), consider implementing direct
   browser-to-storage upload where the frontend gets a presigned URL and
   uploads directly without going through your backend.
