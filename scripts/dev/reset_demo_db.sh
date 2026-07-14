#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONFIRM_RESET:-}" != "RESET_DEMO_DB" ]]; then
  echo "Refusing to reset the database without CONFIRM_RESET=RESET_DEMO_DB."
  echo "This deletes local demo data and recreates the seeded database."
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"
CONFIRM_RESET=RESET_UAT_DB "${SCRIPT_DIR}/reset_uat_db.sh"
