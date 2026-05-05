# Skills Index

Skills are domain-specific guidance files. Each `<topic>.md` follows this fixed shape:

- **When to use** — trigger phrases that should pull the skill in
- **Primitive** — the imports and env setup
- **Backend example** — a complete, copy-pasteable FastAPI snippet
- **Frontend example** — a complete, copy-pasteable React snippet (if applicable)
- **Env vars** — what to add to `backend/.env` and how to generate values
- **Gotchas** — the specific failure modes the agent keeps making

Rules:

- Read `skills/<topic>.md` BEFORE writing any code in that domain.
- Skills OVERRIDE the general guidance in `BASE.md` for their specific topic.
- If no skill matches, fall back to `BASE.md` conventions.
- Never hand-roll a primitive that a skill covers. Copy the skill's shape exactly
  and adapt only the parts the task requires.

## Available skills

- **auth** — Email/password authentication with JWT, protected routes, login/signup/logout flows, user sessions stored in the app's own MongoDB. Pull in when the task mentions login, signup, register, "sign in", "create an account", user accounts, sessions, logout, authentication, protected pages, or "users can only see X if logged in".
- **database** — MongoDB CRUD patterns: list endpoints, ObjectId round-tripping, request/document/response model separation, pagination, user-scoped queries, and startup indexes. Pull in when the task involves listing records, dashboards, feeds, tables, reading/updating a single record by ID, filtering by the current user, or anything that returns more than one document. Simple single-form-to-collection cases (like a contact form) are already covered by BASE.md — do NOT pull this skill in for them.
- **storage** — File uploads and storage using Dunea's presigned URL system. Pull in when the task mentions file uploads, image uploads, user avatars, profile pictures, document storage, media hosting, S3, or "users can upload files". Uses `DUNEA_STORAGE_API` for secure presigned URLs — never hardcode S3 credentials.
