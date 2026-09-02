#!/usr/bin/env bash
set -euo pipefail

SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALLER="$SOURCE/install.py"

if [ ! -f "$INSTALLER" ]; then
  echo "ERROR: CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED: $INSTALLER is missing." >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: Python 3.9+ is required. Install it from https://www.python.org/downloads/ and retry:" >&2
  echo "  python3 \"$INSTALLER\" $*" >&2
  exit 1
fi

exec python3 "$INSTALLER" "$@"
