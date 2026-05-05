# auth — Email/Password Authentication

## When to use

Pull this skill in whenever the task mentions login, signup, register, sign-in,
create-an-account, logout, "users can sign in", "protected page", "requires
login", user accounts, sessions, or "only show X to logged-in users". Do NOT
hand-roll JWT, bcrypt, or session cookies — use the shape below exactly.

## Primitive

Email/password auth stored in the app's own MongoDB (`db.users`), with short-lived
JWTs in `Authorization: Bearer <token>` headers and the token persisted in
`localStorage` on the frontend. The backend uses:

- `passlib[bcrypt]` — password hashing (already pre-installed)
- `python-jose[cryptography]` — JWT signing/verification (already pre-installed)
- `pymongo` — user storage via the existing `from database import db`

Required environment variable — add to `backend/.env` before starting the server:

```
JWT_SECRET=<random 32+ char string>
```

Generate with: `python -c 'import secrets; print(secrets.token_urlsafe(32))'`.
Paste the output as the value. Do NOT reuse a placeholder.

## Backend example

Create `backend/routes/auth.py`:

```python
from datetime import datetime, timedelta, timezone
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from bson import ObjectId
from bson.errors import InvalidId

from database import db

router = APIRouter()
bearer = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"
EXPIRES_MINUTES = 60 * 24 * 7  # 7 days


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _make_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=EXPIRES_MINUTES),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def _public_user(doc: dict) -> dict:
    return {"id": str(doc["_id"]), "email": doc["email"]}


@router.post("/register")
async def register(data: RegisterRequest):
    if db.users.find_one({"email": data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    result = db.users.insert_one({
        "email": data.email,
        "password_hash": pwd_context.hash(data.password),
        "created_at": datetime.now(timezone.utc),
    })
    user = db.users.find_one({"_id": result.inserted_id})
    return {"token": _make_token(str(user["_id"])), "user": _public_user(user)}


@router.post("/login")
async def login(data: LoginRequest):
    user = db.users.find_one({"email": data.email})
    if not user or not pwd_context.verify(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": _make_token(str(user["_id"])), "user": _public_user(user)}


async def require_login(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    try:
        payload = jwt.decode(creds.credentials, SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return _public_user(user)
    except (JWTError, InvalidId):
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.get("/me")
async def me(user: dict = Depends(require_login)):
    return user
```

Register the router in `backend/main.py` (add these two lines alongside the
existing `health_router` registration):

```python
from routes.auth import router as auth_router
app.include_router(auth_router, prefix="/api/auth")
```

Protect any route in any other router by adding `Depends(require_login)`:

```python
from routes.auth import require_login

@router.get("/posts")
async def list_posts(user: dict = Depends(require_login)):
    return list(db.posts.find({"owner_id": user["id"]}))
```

## Frontend example

Create `frontend/src/lib/auth.ts` — the auth store and a helper for attaching
the bearer token to authenticated fetches:

```ts
import { create } from 'zustand';

type User = { id: string; email: string };

type AuthState = {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
};

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem('dunea_token'),
  isLoading: true,

  login: async (email, password) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail ?? 'Login failed');
    }
    const { token, user } = await res.json();
    localStorage.setItem('dunea_token', token);
    set({ user, token, isLoading: false });
  },

  register: async (email, password) => {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(err.detail ?? 'Registration failed');
    }
    const { token, user } = await res.json();
    localStorage.setItem('dunea_token', token);
    set({ user, token, isLoading: false });
  },

  logout: () => {
    localStorage.removeItem('dunea_token');
    set({ user: null, token: null, isLoading: false });
  },

  fetchMe: async () => {
    const token = get().token;
    if (!token) {
      set({ isLoading: false });
      return;
    }
    const res = await fetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      set({ user: await res.json(), isLoading: false });
    } else {
      get().logout();
    }
  },
}));

// Use this for any fetch that hits a protected backend route.
export function authHeaders(): HeadersInit {
  const token = useAuth.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}
```

Call `useAuth().fetchMe()` once on app mount in `frontend/src/main.tsx` so the
store rehydrates from localStorage:

```tsx
// frontend/src/main.tsx (inside the render setup, before ReactDOM.render)
import { useAuth } from '@/lib/auth';
useAuth.getState().fetchMe();
```

Minimal login page using react-hook-form + zod + shadcn/ui (the template's
established pattern):

```tsx
// frontend/src/pages/Login.tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/lib/auth';

const schema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'At least 8 characters'),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const login = useAuth((s) => s.login);
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    try {
      await login(values.email, values.password);
      toast.success('Welcome back!');
      navigate('/');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Login failed');
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="mx-auto mt-24 w-full max-w-sm space-y-4">
      <h1 className="text-2xl font-semibold">Sign in</h1>
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" {...register('email')} />
        {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
      </div>
      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <Input id="password" type="password" {...register('password')} />
        {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
      </div>
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? 'Signing in…' : 'Sign in'}
      </Button>
      <p className="text-center text-sm text-muted-foreground">
        No account? <Link to="/register" className="underline">Create one</Link>
      </p>
    </form>
  );
}
```

The register page is structurally identical — same schema, same form, calls
`useAuth((s) => s.register)` instead of `login`. Copy the file and rename.

Protecting a page is a one-liner pattern — add this check at the top of any
protected component:

```tsx
const user = useAuth((s) => s.user);
const isLoading = useAuth((s) => s.isLoading);
if (isLoading) return null; // or a spinner
if (!user) return <Navigate to="/login" replace />;
```

Add both routes to `frontend/src/routes.tsx`: `/login` → `<LoginPage />`,
`/register` → `<RegisterPage />`.

## Env vars

Add to `backend/.env`:

```
JWT_SECRET=<paste output of: python -c 'import secrets; print(secrets.token_urlsafe(32))'>
```

Never commit the value. Never use a placeholder string — the backend will start
with a weak secret and fail silently under real use. Always generate fresh.

## Gotchas

1. **Don't use `OAuth2PasswordRequestForm`**. The template's frontend sends
   JSON via `fetch()`, and form parsers choke on JSON with a confusing
   `{"detail":"There was an error parsing the body"}` 400 error. Use the
   `RegisterRequest` / `LoginRequest` Pydantic models shown above.
2. **Don't hash passwords with anything other than the `passlib` `CryptContext`**
   shown above. Not plain `bcrypt.hashpw`, not `hashlib.sha256`, not PBKDF2 by
   hand. `passlib` handles salting, algorithm upgrades, and timing-safe
   comparison for you.
3. **Don't store the raw password anywhere.** Not in logs, not in the DB, not
   in the JWT payload, not in the response body. The only field that should
   ever touch persistence is `password_hash`.
4. **Don't stuff sensitive data (name, role, email) into the JWT payload.**
   JWTs are readable by anyone who has the token — they're signed, not
   encrypted. Put only the user ID in `sub` and look the rest up from MongoDB
   in `require_login`.
5. **Don't forget to add `JWT_SECRET` to `backend/.env` BEFORE calling
   `start_server`.** The backend will crash on startup with
   `KeyError: 'JWT_SECRET'` and the preview will never come up. Add the env
   var first, then start.
6. **Don't add trailing slashes to the routes** (`@router.post("/login")`, not
   `@router.post("/login/")`). Trailing slashes trigger 307 redirects that drop
   the request body on some clients, and the first sign a user sees is an
   opaque "Unexpected token '<'" JSON error.
