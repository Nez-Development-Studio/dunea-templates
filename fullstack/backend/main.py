from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from routes.health import router as health_router

app = FastAPI(title="Dunea API")

FRONTEND_DIST = (Path(__file__).resolve().parent.parent / "frontend" / "dist").resolve()
INDEX_FILE = FRONTEND_DIST / "index.html"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")


def resolve_frontend_file(path: str) -> Path | None:
    if not FRONTEND_DIST.exists():
        return None

    requested = (FRONTEND_DIST / path).resolve()

    # Keep requests inside the built frontend directory.
    if requested != FRONTEND_DIST and FRONTEND_DIST not in requested.parents:
        return None

    if requested.is_file():
        return requested

    if INDEX_FILE.is_file():
        return INDEX_FILE

    return None


@app.get("/", include_in_schema=False)
async def serve_root():
    if not INDEX_FILE.is_file():
        raise HTTPException(status_code=404, detail="Frontend build not found")

    return FileResponse(INDEX_FILE)


@app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
async def serve_frontend(full_path: str):
    # Never intercept API requests — let them fall through to the API routers
    # (or return a real 404) so JSON clients never receive HTML by accident.
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")

    resolved = resolve_frontend_file(full_path)

    if resolved is None:
        raise HTTPException(status_code=404, detail="Not Found")

    return FileResponse(resolved)
