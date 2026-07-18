#!/usr/bin/env bash
set -euo pipefail

WEB_BASE_URL="${WEB_BASE_URL:-http://localhost:3000}"
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"

ADMIN_EMAIL="${ADMIN_EMAIL:-admin@school.example}"
TEACHER_EMAIL="${TEACHER_EMAIL:-teacher@school.example}"
STUDENT_EMAIL="${STUDENT_EMAIL:-student@school.example}"
DEMO_PASSWORD="${DEMO_PASSWORD:-Password123!}"

PRACTICE_TASK_ID="${PRACTICE_TASK_ID:-dddddddd-dddd-4ddd-8ddd-dddddddddd01}"
EXAM_TASK_ID="${EXAM_TASK_ID:-dddddddd-dddd-4ddd-8ddd-dddddddddd02}"
RUBRIC_ID="${RUBRIC_ID:-cccccccc-cccc-4ccc-8ccc-ccccccccccc1}"

tmp_dir="$(mktemp -d)"
cleanup() {
  rm -rf "${tmp_dir}"
}
trap cleanup EXIT

fail() {
  printf 'FAIL %s\n' "$1" >&2
  exit 1
}

pass() {
  printf 'PASS %s\n' "$1"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing command: $1"
}

http_status() {
  curl -sS -o /dev/null -w '%{http_code}' "$1"
}

expect_status() {
  local label="$1"
  local url="$2"
  local expected="$3"
  local actual
  actual="$(http_status "${url}")"
  [[ "${actual}" == "${expected}" ]] || fail "${label}: expected HTTP ${expected}, got ${actual}"
  pass "${label}"
}

expect_contains() {
  local label="$1"
  local body="$2"
  local needle="$3"
  [[ "${body}" == *"${needle}"* ]] || fail "${label}: expected response to contain ${needle}"
  pass "${label}"
}

api_post() {
  local cookie_file="$1"
  local path="$2"
  local payload="$3"
  curl -sS \
    -b "${cookie_file}" \
    -H 'content-type: application/json' \
    -d "${payload}" \
    "${API_BASE_URL}${path}"
}

login_as() {
  local label="$1"
  local email="$2"
  local cookie_file="$3"
  local body
  body="$(
    curl -sS \
      -c "${cookie_file}" \
      -H 'content-type: application/json' \
      -d "{\"email\":\"${email}\",\"password\":\"${DEMO_PASSWORD}\"}" \
      "${API_BASE_URL}/api/auth/login"
  )"
  expect_contains "${label} login" "${body}" '"success":true'
}

require_cmd curl

printf 'English AI Writing demo smoke\n'
printf 'Web: %s\n' "${WEB_BASE_URL}"
printf 'API: %s\n\n' "${API_BASE_URL}"

expect_status "web login route" "${WEB_BASE_URL}/login" "200"
expect_status "internal prototype route" "${WEB_BASE_URL}/prototype" "200"
expect_status "parent route hidden" "${WEB_BASE_URL}/parent/progress" "404"

health_body="$(curl -sS "${API_BASE_URL}/api/health")"
expect_contains "api health" "${health_body}" '"success":true'
expect_contains "api redis health" "${health_body}" '"redis":"ok"'

admin_cookie="${tmp_dir}/admin.cookies"
teacher_cookie="${tmp_dir}/teacher.cookies"
student_cookie="${tmp_dir}/student.cookies"

login_as "admin" "${ADMIN_EMAIL}" "${admin_cookie}"
ai_body="$(curl -sS -b "${admin_cookie}" -X POST "${API_BASE_URL}/api/admin/ai/test")"
expect_contains "real LLM connection" "${ai_body}" '"ok":true'

login_as "teacher" "${TEACHER_EMAIL}" "${teacher_cookie}"
prompt_body="$(
  api_post "${teacher_cookie}" "/api/teacher/questions/generate" \
    "{\"level\":\"P5\",\"mode\":\"PRACTICE\",\"teaching_focus\":\"narrative writing with a clear beginning, middle and ending\",\"word_minimum\":120,\"word_maximum\":180,\"rubric_id\":\"${RUBRIC_ID}\"}"
)"
expect_contains "real prompt generation" "${prompt_body}" '"success":true'

login_as "student" "${STUDENT_EMAIL}" "${student_cookie}"
grammar_body="$(
  api_post "${student_cookie}" "/api/suggestions/check" \
    "{\"task_id\":\"${PRACTICE_TASK_ID}\",\"text\":\"Yesterday I go to school and I has a good time.\",\"language\":\"en-US\",\"check_mode\":\"FULL\"}"
)"
expect_contains "real grammar check" "${grammar_body}" '"service_status":"ok"'
expect_contains "grammar rule returned" "${grammar_body}" '"NON3PRS_VERB'

exam_body="$(
  api_post "${student_cookie}" "/api/suggestions/check" \
    "{\"task_id\":\"${EXAM_TASK_ID}\",\"text\":\"Yesterday I go to school and I has a good time.\",\"language\":\"en-US\",\"check_mode\":\"FULL\"}"
)"
expect_contains "exam suggestions blocked" "${exam_body}" '"error_code":"ACCESS_DENIED"'

printf '\nDemo smoke passed.\n'
