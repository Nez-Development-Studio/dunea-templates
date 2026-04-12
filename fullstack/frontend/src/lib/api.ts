/**
 * Thin fetch wrapper for calling the backend at /api/*.
 *
 * - Sets Content-Type: application/json on requests with a body
 * - Validates the response is actually JSON before parsing (catches the
 *   "Unexpected token '<', "<!doctype"' class of bugs caused by route
 *   mismatches that fall through to the SPA fallback)
 * - Surfaces backend `detail` / `message` fields in thrown errors so toasts
 *   can show meaningful text
 *
 * Usage:
 *   const data = await api<{ id: string }>('/api/contact', {
 *     method: 'POST',
 *     body: JSON.stringify({ name, email, message }),
 *   });
 */
export async function api<T = unknown>(input: string, init?: RequestInit): Promise<T> {
  const hasBody = init?.body !== undefined && init.body !== null;
  const headers: HeadersInit = {
    ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
    Accept: 'application/json',
    ...(init?.headers ?? {}),
  };

  const response = await fetch(input, { ...init, headers });
  const contentType = response.headers.get('content-type') ?? '';

  // The backend should always respond with JSON. If we got HTML, the request
  // hit the SPA fallback — almost always a wrong path, wrong method, or
  // missing route registration in backend/main.py.
  if (!contentType.includes('application/json')) {
    const preview = (await response.text()).slice(0, 120);
    throw new Error(
      `Backend returned ${contentType || 'no content-type'} (status ${response.status}) for ${input}. ` +
        `Likely a route mismatch — check the FastAPI route path and that it's registered in backend/main.py. ` +
        `Response preview: ${preview}`,
    );
  }

  const data = (await response.json().catch(() => null)) as
    | (T & { detail?: string; message?: string })
    | null;

  if (!response.ok) {
    const message = data?.detail || data?.message || `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return data as T;
}
