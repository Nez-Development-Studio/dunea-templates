# Dunea Templates

Project templates for [Dunea](https://dunea.dev) sandboxes.

## Available Templates

| Template | Description |
|----------|-------------|
| **fullstack** | React + FastAPI + MongoDB starter with Vite, Tailwind CSS, and shadcn/ui |

## Usage

Templates are automatically fetched when creating a new Dunea project. The sandbox base image has pre-installed dependencies, and template source files are overlaid at creation time.

## Template Structure

Each template contains:
- `manifest.json` - Template metadata
- `frontend/src/` - React application source
- `frontend/index.html` - Entry point
- `backend/` - FastAPI application (main.py, routes/, config.py, database.py)
- `BASE.md` - Architecture guide for the AI agent
- `start.sh` - Development server startup script
- `Dockerfile` - Production build configuration

## Adding Templates

1. Create a new directory with your template files
2. Add a `manifest.json` with template metadata
3. Update `registry.json` to include your template
4. Submit a PR

## License

MIT
