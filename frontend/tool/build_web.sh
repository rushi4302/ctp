#!/bin/sh
set -eu

if [ -z "${API_BASE_URL:-}" ]; then
  echo "Set API_BASE_URL to the reachable FastAPI origin, for example http://127.0.0.1:8000" >&2
  exit 2
fi

if [ -n "${MAPS_API_KEY:-}" ]; then
  flutter build web --release \
    --dart-define="API_BASE_URL=${API_BASE_URL}" \
    --dart-define=MAPS_API_KEY_CONFIGURED=true
else
  flutter build web --release --dart-define="API_BASE_URL=${API_BASE_URL}"
fi

# Google Maps browser keys are client-visible by design. The restricted key is
# supplied only by the local build environment and injected into build output.
if [ -n "${MAPS_API_KEY:-}" ]; then
  python3 - <<'PY'
from html import escape
import os
from pathlib import Path
from urllib.parse import quote

index = Path("build/web/index.html")
html = index.read_text()
key = quote(os.environ["MAPS_API_KEY"], safe="")
tag = f'<script src="https://maps.googleapis.com/maps/api/js?key={escape(key, quote=True)}"></script>\n'
marker = '<script src="flutter_bootstrap.js" async></script>'
if marker not in html:
    raise SystemExit("Could not find Flutter web bootstrap marker in generated index.html")
if "maps.googleapis.com/maps/api/js" not in html:
    html = html.replace(marker, tag + marker)
index.write_text(html)
PY
fi

echo "Web build created at frontend/build/web."
