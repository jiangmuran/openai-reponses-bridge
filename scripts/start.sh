#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"

UPSTREAM_URL=""
API_KEY=""
PORT="8000"

while [ $# -gt 0 ]; do
  case "$1" in
    --upstream)
      UPSTREAM_URL="$2"
      shift 2
      ;;
    --api-key)
      API_KEY="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required but was not found in PATH." >&2
  exit 1
fi

if [ ! -d "${VENV_DIR}" ]; then
  "${ROOT_DIR}/scripts/setup.sh"
fi

if [ -z "${UPSTREAM_URL}" ]; then
  read -r -p "Enter upstream base URL: " UPSTREAM_URL
fi

if [ -z "${UPSTREAM_URL}" ]; then
  echo "Upstream URL is required." >&2
  exit 1
fi

UPSTREAM_URL="${UPSTREAM_URL%/}"
UPSTREAM_HAS_V1=0
if [[ "${UPSTREAM_URL}" == */v1 ]]; then
  UPSTREAM_HAS_V1=1
fi

auth_header=()
if [ -n "${API_KEY}" ]; then
  auth_header=(-H "Authorization: Bearer ${API_KEY}")
fi

check_endpoint_get() {
  local url="$1"
  local code
  code=$(curl -sS -o /dev/null -w "%{http_code}" "${auth_header[@]}" "$url" || true)

  case "$code" in
    200|201|204|301|302|303|307|308|401|403|405|429)
      echo "OK: $url ($code)"
      return 0
      ;;
    *)
      echo "FAIL: $url ($code)" >&2
      return 1
      ;;
  esac
}

check_endpoint_post() {
  local url="$1"
  local code
  code=$(curl -sS -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" \
    "${auth_header[@]}" -d '{}' "$url" || true)

  case "$code" in
    200|201|204|301|302|303|307|308|400|401|403|405|415|422|429)
      echo "OK: $url ($code)"
      return 0
      ;;
    *)
      echo "FAIL: $url ($code)" >&2
      return 1
      ;;
  esac
}

echo "Validating upstream..."
check_endpoint_get "${UPSTREAM_URL}" || exit 1
check_endpoint_post "${UPSTREAM_URL}/responses" || exit 1
if [ "${UPSTREAM_HAS_V1}" -eq 0 ]; then
  check_endpoint_post "${UPSTREAM_URL}/v1/responses" || exit 1
fi

export UPSTREAM_BASE_URL="${UPSTREAM_URL}"
if [ -n "${API_KEY}" ]; then
  export UPSTREAM_API_KEY="${API_KEY}"
fi

"${VENV_DIR}/bin/python" -m uvicorn src.main:app --host 0.0.0.0 --port "${PORT}"
