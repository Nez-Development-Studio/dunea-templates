#!/bin/bash
# Start dev server for preview (idempotent — skips if already running)

# Restore supervisord config if it was modified or deleted by the LLM agent
if [ -f /opt/supervisord.conf.bak ]; then
  if ! cmp -s /opt/supervisord.conf.bak /etc/supervisor/conf.d/dunea.conf 2>/dev/null; then
    cp /opt/supervisord.conf.bak /etc/supervisor/conf.d/dunea.conf
    supervisorctl reread >/dev/null 2>&1
    supervisorctl update >/dev/null 2>&1
  fi
fi

# Frontend only (landing pages have no backend)
if ! lsof -i :5173 -sTCP:LISTEN >/dev/null 2>&1; then
  supervisorctl start frontend
fi
