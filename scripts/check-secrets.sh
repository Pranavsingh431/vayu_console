#!/usr/bin/env bash
#
# Fail if anything secret-bearing is tracked by git.
#
# This repository is public and `.env` holds live API credentials, so a single
# careless `git add -f` would leak them permanently. `.gitignore` is the first
# line of defence; this is the second. Runs in CI and as a pre-commit hook.
#
# Portable to bash 3.2 (macOS system bash) — no mapfile, no associative arrays.
#
# Usage: scripts/check-secrets.sh

set -uo pipefail

fail=0

# --- 1. No environment file may be tracked, except placeholder examples. ------
tracked_env=$(git ls-files | grep -E '(^|/)\.env' | grep -v '\.env\.example$' || true)
if [ -n "$tracked_env" ]; then
  echo "::error::Environment files are tracked by git:"
  echo "$tracked_env" | sed 's/^/  /'
  echo "  Remove with: git rm --cached <file>"
  fail=1
fi

# --- 2. No high-signal credential pattern in tracked text files. --------------
# Each pattern matches a key format this project actually uses, which keeps
# false positives low. `.env.example` holds names, never values, so it is exempt.
scan() {
  description=$1
  pattern=$2

  matches=$(git ls-files -z -- '*.py' '*.ts' '*.tsx' '*.js' '*.mjs' '*.json' '*.yml' '*.yaml' '*.md' '*.toml' \
    | grep -zv '\.env\.example$' \
    | xargs -0 grep -nE "$pattern" 2>/dev/null || true)

  if [ -n "$matches" ]; then
    echo "::error::$description"
    echo "$matches" | sed 's/^/  /'
    fail=1
  fi
}

# NASA Earthdata bearer tokens, and JWTs generally.
scan "A JWT appears in a tracked file." \
  'eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}'

# data.gov.in keys (40+ hex) and FIRMS map keys (32 hex), anchored to an
# assignment so that lockfile digests and git SHAs do not trip the check.
scan "A hardcoded credential appears in a tracked file." \
  '(API_KEY|MAP_KEY|SECRET|TOKEN|PASSWORD)[A-Za-z_]*[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9]{24,}'

# OpenRouter keys.
scan "An OpenRouter key appears in a tracked file." \
  'sk-or-v1-[A-Za-z0-9]{16,}'

if [ "$fail" -eq 0 ]; then
  echo "Secret scan passed: no credentials or environment files are tracked."
fi

exit "$fail"
