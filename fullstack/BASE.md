# Project Architecture Guide

## Stack

- **Frontend**: Vite 6 + React 18 + TypeScript + Tailwind CSS v3
- **Backend**: Python FastAPI + PyMongo
- **Database**: MongoDB on `localhost:27017` (no auth)

## Directory Layout

```
/home/project/
├── frontend/
│   ├── package.json              # Pre-installed deps — NEVER overwrite
│   ├── vite.config.ts            # Platform-managed — use edit_file only
│   ├── tsconfig.json             # Path alias: @/ → ./src/
│   ├── tailwind.config.js
│   ├── components.json           # shadcn config
│   ├── index.html
│   └── src/
│       ├── main.tsx              # App entry — BrowserRouter, Toaster
│       ├── App.tsx               # Renders <AppRoutes />
│       ├── routes.tsx            # All route definitions — update when adding pages
│       ├── index.css             # Tailwind directives, CSS variables, font imports
│       ├── lib/
│       │   └── utils.ts          # cn() utility for class merging
│       └── components/
│           └── ui/               # shadcn/ui — pre-installed
│
├── backend/
│   ├── main.py                   # FastAPI app — register new routers here
│   ├── config.py                 # Settings via pydantic-settings (.env support)
│   ├── database.py               # PyMongo client — use `db.<collection>` for queries
│   ├── pyproject.toml            # Python deps — use `uv add` to add new ones
│   ├── uv.lock                   # Lockfile — deterministic builds, auto-managed
│   └── routes/
│       └── health.py             # GET /api/health
│
└── BASE.md                       # This file
```

## Key Patterns

### Frontend

- **Routing**: All routes in `frontend/src/routes.tsx` using react-router-dom.
- **Path alias**: `@/` maps to `frontend/src/`.
- **API calls**: Use the `api()` helper from `@/lib/api` — `import { api } from '@/lib/api'`. It validates the response is JSON, surfaces backend error messages, and gives clear errors when a route is misconfigured. Vite proxies `/api` to the backend at `localhost:8000`.
- **State**: Zustand for client state. React Hook Form + Zod for forms.
- **Notifications**: Sonner is pre-installed AND `<Toaster />` is already mounted
  in `frontend/src/main.tsx` — you do NOT need to add a Toaster component anywhere.
  In any file that shows a notification, add `import { toast } from 'sonner'` at
  the top and call `toast.success('Saved!')`, `toast.error('Something went wrong')`,
  `toast.info(...)`, `toast.warning(...)`, or `toast.loading(...)`. The `toast`
  function is NOT globally available — you must import it per file, just like any
  other ES module. Example:
  ```tsx
  import { toast } from 'sonner';

  async function handleSubmit(data: FormData) {
    try {
      await api('/api/contact', { method: 'POST', body: JSON.stringify(data) });
      toast.success('Message sent!');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Something went wrong');
    }
  }
  ```
  Do NOT import `Toaster` from `@/components/ui/sonner` — that shadcn wrapper
  depends on `next-themes`, which is not installed. Import directly from the
  `sonner` package for any Toaster-related type (but you generally don't need to,
  since it's already mounted).
- **Icons**: Lucide React — `import { Icon } from 'lucide-react'`
- **Class merging**: `import { cn } from '@/lib/utils'`
- **shadcn/ui**: Pre-installed at `@/components/ui/<name>`. Import directly.
  Exception: `@/components/ui/sonner` is broken (missing `next-themes` dep) —
  don't use it. The Toaster is already mounted from the `sonner` package.

### Backend

- **New routes**: Create a file in `backend/routes/`, then register in `backend/main.py`:
  ```python
  from routes.your_module import router as your_router
  app.include_router(your_router, prefix="/api/your-prefix")
  ```
- **Request bodies**: ALWAYS use a Pydantic `BaseModel` parameter. NEVER use `Form()`, `File()`, or
  `OAuth2PasswordRequestForm` — the frontend `api()` helper sends `application/json` via `fetch()`,
  and form parsers choke on JSON with an opaque `{"detail":"There was an error parsing the body"}` 400.
  For login/auth, define your own `LoginRequest(BaseModel)`. The only exception is real file uploads,
  where you use `UploadFile` directly (no `File()` wrapper) and the frontend sends `FormData`.
  Route paths must NOT have trailing slashes (`@router.post("/contact")`, or `@router.post("")` for
  the router's prefix root) — trailing slashes trigger 307 redirects that drop the body.

  Canonical POST example — copy this shape for every form/CTA endpoint:
  ```python
  from fastapi import APIRouter
  from pydantic import BaseModel, EmailStr
  from database import db

  router = APIRouter()

  class AppointmentRequest(BaseModel):
      name: str
      email: EmailStr
      phone: str
      notes: str | None = None

  @router.post("/appointments")
  async def create_appointment(data: AppointmentRequest):
      result = db.appointments.insert_one(data.model_dump())
      return {"id": str(result.inserted_id)}
  ```
- **Database**: Use `from database import db`, then `db.<collection>.find()`, `.insert_one()`, etc.
- **New deps**: Run `cd /home/project/backend && uv add <package>` — installs AND records the dependency in one step. Never edit pyproject.toml manually for deps.

## Skills — domain-specific guidance

The `skills/` directory contains per-topic guidance files. `skills/INDEX.md` is
a one-line registry of what's available and must be read on every task (it's
in your initial read batch with BASE.md). If any skill's description matches
what you're about to build, read that `skills/<topic>.md` before writing any
code. Skills OVERRIDE the general guidance in this file for their specific
topic — copy the skill's shape exactly and adapt only the parts the task
requires.

Do NOT hand-roll auth, JWT signing, password hashing, payment flows, or other
sensitive primitives — if a skill exists for that domain, use the code shape
it provides. If you catch yourself writing `jwt.encode`, `bcrypt.hashpw`, or
a Stripe webhook handler from scratch, stop and re-read the relevant skill.

## Critical Rules

1. **NEVER overwrite** `frontend/package.json` — use `pnpm add <pkg>` to add new ones.
2. **NEVER overwrite** `frontend/vite.config.ts` — use `edit_file` for changes.
3. **NEVER run** `npm init`, `npx create-vite`, or any scaffolding tool.
4. **Always update** `frontend/src/routes.tsx` when adding new pages.
5. **Always register** new backend routers in `backend/main.py`.

## Services

Managed by supervisord. Start dev servers with:

```bash
bash /home/project/start.sh
```

Or use the `start_server` tool. Preview appears automatically when port 5173 opens.
