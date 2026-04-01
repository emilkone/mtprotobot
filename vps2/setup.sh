#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: setup.sh <vps2_host> <vps2_user> [ssh_key_path]" >&2
  exit 2
fi

VPS2_HOST="$1"
VPS2_USER="$2"
SSH_KEY_PATH="${3:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ssh_opts=()
if [ -n "${SSH_KEY_PATH}" ]; then
  ssh_opts+=("-i" "${SSH_KEY_PATH}")
fi

echo "Ensuring python3 on ${VPS2_USER}@${VPS2_HOST}"
ssh "${ssh_opts[@]}" "${VPS2_USER}@${VPS2_HOST}" "python3 -V >/dev/null 2>&1 || (sudo apt-get update && sudo apt-get install -y python3)"

echo "Uploading checker.py"
scp "${ssh_opts[@]}" "${ROOT_DIR}/vps2/checker.py" "${VPS2_USER}@${VPS2_HOST}:/home/${VPS2_USER}/checker.py"
ssh "${ssh_opts[@]}" "${VPS2_USER}@${VPS2_HOST}" "chmod +x /home/${VPS2_USER}/checker.py && python3 /home/${VPS2_USER}/checker.py '[]' >/dev/null"

echo "Done"

