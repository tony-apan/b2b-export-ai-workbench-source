#!/usr/bin/env bash
# Install this skill for local AI tools by symlinking THIS repo into each tool's
# skills folder. Works with any tool that discovers the SKILL.md format from a
# skills directory (Claude Code, Codex, WorkBuddy, …).
#
#   ./install.sh                       # auto-detect installed tools and link into each
#   ./install.sh codex                 # only Codex
#   ./install.sh claude workbuddy      # pick specific tools
#   ./install.sh --dir=/path/to/skills # any other tool's skills dir (unknown / self-managed)
#   ./install.sh claude --force        # repoint an existing symlink
#
# Idempotent. NEVER deletes a real file or directory — it only creates symlinks,
# and --force only ever replaces an existing SYMLINK.
#
# NOTE: tools that don't use the SKILL.md-in-a-skills-dir format (e.g. plugin-based
# ones) won't discover it this way. For those, just point the AI at this repo's
# SKILL.md directly as its operating contract — no install needed.
set -euo pipefail

SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANONICAL_BLOCK_CODE="CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED"

# This must be the real skill repo. Derive the skill name from SKILL.md so the
# link name always matches the contract's declared name.
if [ ! -f "$SOURCE/SKILL.md" ]; then
  echo "ERROR: $SOURCE/SKILL.md not found — run install.sh from inside the cloned repo." >&2
  exit 1
fi
NAME="$(awk -F': *' '/^name:/{gsub(/["'\'' ]/,"",$2); print $2; exit}' "$SOURCE/SKILL.md")"
NAME="${NAME:-$(basename "$SOURCE")}"

# Known SKILL.md-format tools -> their skills directory.
tool_dir() {
  case "$1" in
    codex)     echo "$HOME/.codex/skills" ;;
    claude)    echo "$HOME/.claude/skills" ;;
    workbuddy) echo "$HOME/.workbuddy/skills" ;;
    *) return 1 ;;
  esac
}
KNOWN_TOOLS="codex claude workbuddy"

FORCE=0
ROOTS=()
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --dir=*) p="${arg#--dir=}"; p="${p/#\~/$HOME}"; ROOTS+=("$p") ;;
    /*)      ROOTS+=("$arg") ;;                       # an absolute skills-dir path
    codex|claude|workbuddy) ROOTS+=("$(tool_dir "$arg")") ;;
    -h|--help)
      echo "Usage: ./install.sh [codex] [claude] [workbuddy] [--dir=/path/to/skills] [--force]"
      echo "  No tool arg: auto-detect installed tools (~/.codex, ~/.claude, ~/.workbuddy) and link into each."
      echo "  --dir=<path>: link into any other tool's skills directory (unknown / self-managed tools)."
      echo "  --force: repoint an existing SYMLINK (never touches a real file or directory)."
      exit 0 ;;
    *) echo "unknown arg: $arg (see --help)" >&2; exit 2 ;;
  esac
done

# Default: auto-detect — install only for tools whose home dir actually exists,
# so we never scatter link dirs for tools you don't have.
if [ "${#ROOTS[@]}" -eq 0 ]; then
  for t in $KNOWN_TOOLS; do
    d="$(tool_dir "$t")"
    [ -d "$(dirname "$d")" ] && ROOTS+=("$d")
  done
fi
if [ "${#ROOTS[@]}" -eq 0 ]; then
  echo "No known tool detected (~/.codex, ~/.claude, ~/.workbuddy). Use --dir=<path> to target one explicitly." >&2
  exit 1
fi

link_one() {
  local root="$1" link="$1/$NAME"
  mkdir -p "$root"
  if [ -L "$link" ]; then
    local cur; cur="$(readlink "$link")"
    if [ "$cur" = "$SOURCE" ]; then
      echo "  = $link already links here"
      return 0
    fi
    if [ "$FORCE" -eq 1 ]; then
      rm "$link"                       # removes only the symlink, not its target
      ln -s "$SOURCE" "$link"
      echo "  ~ $link repointed (was -> $cur)"
      return 0
    fi
    echo "  ! $link is a symlink to $cur — re-run with --force to repoint" >&2
    return 1
  fi
  if [ -e "$link" ]; then
    echo "  x $link exists as a REAL file/dir — refusing to touch it; move it aside first" >&2
    return 1
  fi
  ln -s "$SOURCE" "$link"
  echo "  + $link -> $SOURCE"
}

echo "Preparing Skill runtime before creating any install link:"
runtime_resolved=0
runtime_json=""
if [ ! -f "$SOURCE/scripts/resolve_website_content_ops_root.py" ]; then
  echo "  FAIL resolver missing: $SOURCE/scripts/resolve_website_content_ops_root.py" >&2
  exit 1
fi

set +e
runtime_json="$(python3 "$SOURCE/scripts/resolve_website_content_ops_root.py" --start "$SOURCE" --json 2>&1)"
resolver_rc=$?
set -e
if [ "$resolver_rc" -ne 0 ]; then
  runtime_detail="$(printf '%s' "$runtime_json" | python3 -c 'import json,sys
try:
 print(json.load(sys.stdin).get("detail", "resolver failed without structured detail"))
except Exception:
 print(sys.stdin.read() or "resolver failed without structured detail")' 2>/dev/null || true)"
  echo "  BLOCK $CANONICAL_BLOCK_CODE: $runtime_detail" >&2
  echo "Installation stopped before creating Skill links." >&2
  exit 1
fi

json_value() {
  local key="$1"
  printf '%s' "$runtime_json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$key"
}

runtime_root="$(json_value subLibraryRoot)"
runtime_adapter="$(json_value allinCmsRoot)"
runtime_source="$(json_value source)"
runtime_resolved=1

if [ "$runtime_source" = "bundled-runtime" ]; then
  echo "  ok verified bundled runtime resolved: $runtime_root"
  if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
    echo "  BLOCK BUNDLED_RUNTIME_NODE_REQUIRED: Node.js >=20.9.0 and npm are required before this Skill can upload all supported image formats." >&2
    echo "Installation stopped before creating Skill links." >&2
    exit 1
  fi
  if ! node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>20 || (a===20 && b>=9) ? 0 : 1)'; then
    echo "  BLOCK BUNDLED_RUNTIME_NODE_VERSION_UNSUPPORTED: found Node.js $(node -v); required >=20.9.0." >&2
    echo "Installation stopped before creating Skill links." >&2
    exit 1
  fi
  if [ ! -f "$runtime_adapter/package.json" ] || [ ! -f "$runtime_adapter/package-lock.json" ]; then
    echo "  BLOCK BUNDLED_RUNTIME_DEPENDENCY_DESCRIPTOR_MISSING: package.json/package-lock.json missing from $runtime_adapter" >&2
    echo "Installation stopped before creating Skill links." >&2
    exit 1
  fi

  controller_executable="$(json_value controllerExecutable)"
  if [ "$controller_executable" != "True" ] && [ "$controller_executable" != "true" ]; then
    echo "  installing locked bundled runtime dependencies (acorn, ajv, sharp)"
    if ! (cd "$runtime_adapter" && npm ci --omit=dev --no-audit --no-fund); then
      echo "  BLOCK BUNDLED_RUNTIME_DEPENDENCY_INSTALL_FAILED: npm ci failed; check Node/npm availability and network access." >&2
      echo "Installation stopped before creating Skill links." >&2
      exit 1
    fi
  else
    echo "  = locked bundled runtime dependencies already match this bundle"
  fi

  echo "  verifying bundled Adapter registry, index, 250 local tests, and native image dependency"
  if ! (cd "$runtime_adapter" && \
      npm run interfaces:validate && \
      npm run interfaces:index:check && \
      npm test && \
      node --input-type=module -e "await Promise.all([import('acorn'), import('ajv'), import('sharp')])"); then
    echo "  BLOCK BUNDLED_RUNTIME_SELF_TEST_FAILED: local runtime verification failed." >&2
    echo "Installation stopped before creating Skill links." >&2
    exit 1
  fi

  bundle_digest="$(json_value bundleDigest)"
  node_version="$(node -v)"
  python3 - "$runtime_adapter/node_modules/.allincms-runtime-ready.json" "$bundle_digest" "$node_version" <<'PY_MARKER'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
path.write_text(json.dumps({
    "status": "verified",
    "bundleDigest": sys.argv[2],
    "nodeVersion": sys.argv[3],
}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
PY_MARKER

  runtime_json="$(python3 "$SOURCE/scripts/resolve_website_content_ops_root.py" --start "$SOURCE" --json)"
  controller_executable="$(json_value controllerExecutable)"
  if [ "$controller_executable" != "True" ] && [ "$controller_executable" != "true" ]; then
    echo "  BLOCK BUNDLED_RUNTIME_READY_MARKER_REJECTED: resolver did not accept the verified dependency state." >&2
    echo "Installation stopped before creating Skill links." >&2
    exit 1
  fi
  echo "  ok bundled runtime dependencies and self-tests verified"
else
  echo "  ok canonical source checkout resolved: $runtime_root ($runtime_source)"
  echo "  note full-source dependency installation remains owned by that source checkout"
fi

echo "Installing skill '$NAME' from $SOURCE"
rc=0
for root in "${ROOTS[@]}"; do link_one "$root" || rc=1; done

if [ "$rc" -ne 0 ] || [ "$runtime_resolved" -eq 0 ]; then
  echo "Installation incomplete — see failures above." >&2
  exit 1
fi

echo "Verifying installed Skill links:"
for root in "${ROOTS[@]}"; do
  if head -1 "$root/$NAME/SKILL.md" >/dev/null 2>&1; then
    echo "  ok $root/$NAME/SKILL.md reachable"
  else
    echo "  FAIL $root/$NAME/SKILL.md not reachable" >&2; rc=1
  fi
done
if [ "$rc" -ne 0 ]; then
  echo "Installation incomplete — see failures above." >&2
  exit 1
fi

echo "Skill installed and verified runtime ready. Restart the tool if it only discovers skills at startup."
exit 0
