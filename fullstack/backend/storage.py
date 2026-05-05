"""Dunea Storage — File uploads via presigned URLs.

Usage:
    from storage import get_upload_url, get_read_url, list_files

    # Get a presigned URL for uploading
    upload_data = await get_upload_url("avatars/user123.png", "image/png")
    # upload_data = {"url": "https://...", "expiresIn": 900}

    # Get a presigned URL for reading/downloading
    read_url = await get_read_url("avatars/user123.png")
    # Returns the URL string directly

    # List files in a directory
    files = await list_files("uploads/")
    # Returns [{"key": "...", "size": 123, "lastModified": "..."}]

Note: Storage is only available on deployed apps. In local development,
these functions will raise RuntimeError. For local dev, either mock them
or use a local MinIO instance.
"""

from typing import Optional

import httpx

from config import settings

_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    """Get or create the HTTP client for storage API calls."""
    global _client
    if _client is None:
        if not settings.DUNEA_STORAGE_API or not settings.DUNEA_STORAGE_SECRET:
            raise RuntimeError(
                "Storage not configured. DUNEA_STORAGE_API and DUNEA_STORAGE_SECRET "
                "are only set on deployed apps. For local development, mock storage "
                "functions or use a local MinIO instance."
            )
        _client = httpx.AsyncClient(
            headers={"X-Dunea-Storage-Secret": settings.DUNEA_STORAGE_SECRET},
            timeout=30.0,
        )
    return _client


async def get_upload_url(
    path: str, content_type: str = "application/octet-stream", expires_in: int = 900
) -> dict:
    """Get a presigned URL for uploading a file.

    Args:
        path: Where to store the file (e.g., "avatars/user123.png")
        content_type: MIME type of the file
        expires_in: URL validity in seconds (default 15 minutes)

    Returns:
        {"url": "https://...", "expiresIn": 900}
    """
    client = _get_client()
    resp = await client.post(
        f"{settings.DUNEA_STORAGE_API}/upload",
        json={"path": path, "contentType": content_type, "expiresIn": expires_in},
    )
    resp.raise_for_status()
    return resp.json()


async def get_read_url(path: str, expires_in: int = 3600) -> str:
    """Get a presigned URL for reading/downloading a file.

    Args:
        path: File path (e.g., "avatars/user123.png")
        expires_in: URL validity in seconds (default 1 hour)

    Returns:
        The presigned URL string
    """
    client = _get_client()
    resp = await client.get(
        f"{settings.DUNEA_STORAGE_API}/read",
        params={"path": path, "expiresIn": str(expires_in)},
    )
    resp.raise_for_status()
    return resp.json()["url"]


async def get_delete_url(path: str) -> str:
    """Get a presigned URL for deleting a file.

    Args:
        path: File path to delete

    Returns:
        The presigned DELETE URL string
    """
    client = _get_client()
    resp = await client.post(
        f"{settings.DUNEA_STORAGE_API}/delete",
        json={"path": path},
    )
    resp.raise_for_status()
    return resp.json()["url"]


async def list_files(subpath: str = "", max_keys: int = 1000) -> list[dict]:
    """List files in storage.

    Args:
        subpath: Directory path to list (e.g., "uploads/")
        max_keys: Maximum number of files to return

    Returns:
        List of {"key": "...", "size": 123, "lastModified": "..."}
    """
    client = _get_client()
    resp = await client.get(
        f"{settings.DUNEA_STORAGE_API}/list",
        params={"path": subpath, "maxKeys": str(max_keys)},
    )
    resp.raise_for_status()
    return resp.json()["files"]


async def upload_file(path: str, content: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload a file and return its read URL.

    Convenience function that:
    1. Gets a presigned upload URL
    2. Uploads the content
    3. Returns a presigned read URL

    Args:
        path: Where to store the file
        content: File content as bytes
        content_type: MIME type

    Returns:
        Presigned read URL for the uploaded file
    """
    # Get upload URL
    upload_data = await get_upload_url(path, content_type)

    # Upload content
    async with httpx.AsyncClient() as upload_client:
        resp = await upload_client.put(
            upload_data["url"],
            content=content,
            headers={"Content-Type": content_type},
        )
        resp.raise_for_status()

    # Return read URL
    return await get_read_url(path)
