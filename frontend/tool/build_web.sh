#!/bin/sh
set -eu

if [ -z "${API_BASE_URL:-}" ]; then
  echo "Set API_BASE_URL to the reachable FastAPI origin, for example http://127.0.0.1:8000" >&2
  exit 2
fi

flutter build web --release --dart-define="API_BASE_URL=${API_BASE_URL}"

echo "Web build created at frontend/build/web."
