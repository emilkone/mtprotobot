#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

OUT_ENV_DIR="${ROOT_DIR}/data/mtproto"
DATA_DIR="${ROOT_DIR}/data"

# По умолчанию без :443 — на одном VPS часто занят xray/VLESS (Reality).
# При необходимости: MTPROTO_PORTS="8443,2053,2083,2096,4443" (или TELEMT_PORTS — алиас)
if [ -n "${MTPROTO_PORTS:-}" ]; then
  IFS=',' read -r -a PORTS_DEFAULT <<< "${MTPROTO_PORTS// /}"
elif [ -n "${TELEMT_PORTS:-}" ]; then
  IFS=',' read -r -a PORTS_DEFAULT <<< "${TELEMT_PORTS// /}"
else
  PORTS_DEFAULT=("4443" "8443" "2053" "2083" "2096")
fi
if [ "${#PORTS_DEFAULT[@]}" -ne 5 ]; then
  echo "MTPROTO_PORTS must contain exactly 5 comma-separated ports (got ${#PORTS_DEFAULT[@]})" >&2
  exit 1
fi

TLS_DOMAIN="${TLS_DOMAIN:-google.com}"
VPS1_PUBLIC_IP="${VPS1_PUBLIC_IP:-}"

VPS2_HOST="${VPS2_HOST:-}"
VPS2_USER="${VPS2_USER:-checker}"
VPS2_SSH_KEY="${VPS2_SSH_KEY:-}"

usage() {
  cat <<'EOF'
Usage:
  scripts/init.sh

Environment variables:
  TLS_DOMAIN          SNI domain for FakeTLS masking (default: google.com)
  MTPROTO_PORTS       Comma-separated 5 host ports for slots 1..5 (mapped to container 443)
  VPS1_PUBLIC_IP      Public IPv4/hostname of VPS1 (optional; used to precompute links)

  VPS2_HOST           RU VPS host (optional; used by scripts to deploy vps2/checker.py)
  VPS2_USER           RU VPS SSH user (default: checker)
  VPS2_SSH_KEY        Path to SSH private key for RU VPS (optional; ssh-agent also works)

This script:
  - creates data/mtproto/slot_1..5.env with SECRET=ee<hex(domain)><secret32>
  - creates/updates data/proxies.json (initial state)
  - optionally deploys vps2/checker.py to VPS2 if VPS2_HOST is provided

Legacy: TELEMT_PORTS is accepted as an alias for MTPROTO_PORTS.
EOF
}

rand_hex_32() {
  # 16 random bytes -> 32 hex chars
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 16
  else
    python3 - <<'PY'
import secrets
print(secrets.token_hex(16))
PY
  fi
}

make_link() {
  local host="$1"
  local port="$2"
  local tls_domain="$3"
  local secret32="$4"
  local tls_hex
  tls_hex="$(TLS_DOMAIN="${tls_domain}" python3 -c 'import binascii, os; d=os.environ["TLS_DOMAIN"]; print(binascii.hexlify(d.encode("ascii")).decode("ascii"))')"
  printf "https://t.me/proxy?server=%s&port=%s&secret=ee%s%s" "${host}" "${port}" "${tls_hex}" "${secret32}"
}

write_slot_env() {
  local path="$1"
  local tls_domain="$2"
  local secret32="$3"
  local tls_hex full
  tls_hex="$(TLS_DOMAIN="${tls_domain}" python3 -c 'import binascii, os; d=os.environ["TLS_DOMAIN"]; print(binascii.hexlify(d.encode("ascii")).decode("ascii"))')"
  full="ee${tls_hex}${secret32}"
  printf 'SECRET=%s\n' "${full}" > "${path}"
}

generate_configs() {
  mkdir -p "${OUT_ENV_DIR}" "${DATA_DIR}"

  local -a ports=("${PORTS_DEFAULT[@]}")
  local proxies_json="[\n"

  for i in "${!ports[@]}"; do
    local slot=$((i+1))
    local port="${ports[$i]}"
    local secret32
    secret32="$(rand_hex_32)"

    local out="${OUT_ENV_DIR}/slot_${slot}.env"
    write_slot_env "${out}" "${TLS_DOMAIN}" "${secret32}"

    local link=""
    if [ -n "${VPS1_PUBLIC_IP}" ]; then
      link="$(make_link "${VPS1_PUBLIC_IP}" "${port}" "${TLS_DOMAIN}" "${secret32}")"
    fi

    proxies_json+="  {\"slot\": ${slot}, \"port\": ${port}, \"secret32\": \"${secret32}\", \"tls_domain\": \"${TLS_DOMAIN}\", \"link\": \"${link}\"}"
    if [ "${slot}" -lt 5 ]; then
      proxies_json+=",\n"
    else
      proxies_json+="\n"
    fi
  done
  proxies_json+="]\n"

  printf "%b" "${proxies_json}" > "${DATA_DIR}/proxies.json"
  echo "Generated ${OUT_ENV_DIR}/slot_*.env and ${DATA_DIR}/proxies.json"
}

deploy_vps2_checker() {
  if [ -z "${VPS2_HOST}" ]; then
    return 0
  fi

  local ssh_opts=()
  if [ -n "${VPS2_SSH_KEY}" ]; then
    ssh_opts+=("-i" "${VPS2_SSH_KEY}")
  fi

  echo "Deploying vps2/checker.py to ${VPS2_USER}@${VPS2_HOST}"
  scp "${ssh_opts[@]}" "${ROOT_DIR}/vps2/checker.py" "${VPS2_USER}@${VPS2_HOST}:/home/${VPS2_USER}/checker.py"
  ssh "${ssh_opts[@]}" "${VPS2_USER}@${VPS2_HOST}" "python3 -V >/dev/null 2>&1 || (echo 'python3 is required' && exit 1)"
  echo "Deployed checker.py"
}

main() {
  if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    usage
    exit 0
  fi

  generate_configs
  deploy_vps2_checker
}

main "$@"
