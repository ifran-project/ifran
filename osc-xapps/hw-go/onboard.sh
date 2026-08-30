#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
namespace="${OSC_RIC_NAMESPACE:-ricplt}"
service="${OSC_ONBOARDER_SERVICE:-oran-sc-osc-xapp-onboarder}"
local_port="${OSC_ONBOARDER_LOCAL_PORT:-18888}"
request_file="$(mktemp /tmp/hw-go-onboard.XXXXXX.json)"
forward_log="$(mktemp /tmp/hw-go-port-forward.XXXXXX.log)"

cleanup() {
  rm -f "$request_file" "$forward_log"
  if [[ -n "${forward_pid:-}" ]]; then
    kill "$forward_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

jq -n \
  --slurpfile config "$script_dir/config-file.json" \
  --slurpfile schema "$script_dir/schema.json" \
  '{"config-file.json": $config[0], "controls-schema.json": $schema[0]}' \
  > "$request_file"

kubectl port-forward \
  --namespace "$namespace" \
  "service/$service" \
  "$local_port:8888" >"$forward_log" 2>&1 &
forward_pid=$!

for _ in {1..20}; do
  if curl --fail --silent "http://127.0.0.1:$local_port/api/v1/health" >/dev/null; then
    break
  fi
  sleep 1
done

curl --fail --silent --show-error \
  --request POST \
  --header 'Content-Type: application/json' \
  --data-binary "@$request_file" \
  "http://127.0.0.1:$local_port/api/v1/onboard"
printf '\n'
curl --fail --silent --show-error \
  "http://127.0.0.1:$local_port/api/v1/charts"
printf '\n'
