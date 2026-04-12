import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'sonner';
import App from './App';
import './index.css';

// --- Error Overlay ---
// Catches runtime errors, import failures, and unhandled rejections
// and displays them visually in the page so the user can see what broke.

function showErrorOverlay(title: string, message: string, stack?: string) {
  let overlay = document.getElementById('__error-overlay');

  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = '__error-overlay';
    document.body.appendChild(overlay);
  }

  overlay.innerHTML = `
    <div style="
      position: fixed; inset: 0; z-index: 99999;
      background: #1a1a2e; color: #e0e0e0;
      font-family: 'SF Mono', Monaco, Consolas, monospace;
      padding: 32px; overflow: auto;
      display: flex; flex-direction: column; gap: 16px;
    ">
      <div style="display: flex; align-items: center; gap: 12px;">
        <span style="
          background: #e74c3c; color: white; font-weight: 700;
          padding: 4px 12px; border-radius: 6px; font-size: 13px;
        ">ERROR</span>
        <span style="font-size: 16px; font-weight: 600; color: #ff6b6b;">${escapeHtml(title)}</span>
      </div>
      <pre style="
        background: #16213e; border: 1px solid #2a2a4a; border-radius: 8px;
        padding: 20px; margin: 0; white-space: pre-wrap; word-break: break-word;
        font-size: 14px; line-height: 1.6; color: #ffd93d;
      ">${escapeHtml(message)}</pre>
      ${stack ? `<details style="margin-top: 8px;">
        <summary style="cursor: pointer; color: #888; font-size: 13px;">Stack trace</summary>
        <pre style="
          background: #16213e; border: 1px solid #2a2a4a; border-radius: 8px;
          padding: 16px; margin-top: 8px; white-space: pre-wrap; word-break: break-word;
          font-size: 12px; line-height: 1.5; color: #aaa;
        ">${escapeHtml(stack)}</pre>
      </details>` : ''}
    </div>
  `;
}

function escapeHtml(str: string): string {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Catch unhandled errors (including module import failures)
window.addEventListener('error', (event) => {
  showErrorOverlay(
    event.message || 'Runtime Error',
    event.filename
      ? `${event.message}\n\nat ${event.filename}:${event.lineno}:${event.colno}`
      : event.message,
    event.error?.stack,
  );
});

// Catch unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
  const err = event.reason;
  const message = err instanceof Error ? err.message : String(err);
  const stack = err instanceof Error ? err.stack : undefined;

  showErrorOverlay('Unhandled Promise Rejection', message, stack);
});

// --- React Error Boundary ---

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      showErrorOverlay(
        this.state.error.name || 'React Error',
        this.state.error.message,
        this.state.error.stack,
      );

      return null;
    }

    return this.props.children;
  }
}

// --- Render ---

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <App />
      </BrowserRouter>
      {/*
        Toaster is always mounted here so every page can call
        `toast.success()` / `toast.error()` / etc. from sonner without
        re-mounting it. Individual files still need their own
        `import { toast } from 'sonner'` line — see BASE.md.
      */}
      <Toaster richColors position="top-right" />
    </ErrorBoundary>
  </React.StrictMode>,
);
