#!/usr/bin/env bash
# Collect a bounded, repeatable evidence packet for one incident, before any
# model is involved. Every query is read-only and fixed; nothing here takes
# free-form input from the alert except the environment (checked against an
# allowlist) and the route (only used as a query label value, quoted).
#
#   collect-evidence.sh <incident-dir> <prod|staging> [route]
#
# Writes into <incident-dir>/evidence/ and lists what it collected (or what
# failed) in manifest.json. A failed query is recorded, never fatal: partial
# evidence is still evidence.
set -uo pipefail

dir=${1:?incident dir}; env=${2:?environment}; route=${3:-}
[[ $env == prod || $env == staging ]] || { echo "environment must be prod or staging" >&2; exit 2; }
[[ $route =~ ^[A-Za-z0-9_/{}.-]*$ ]] || route=""   # route templates only; anything else is dropped

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
srv=${SRV_DIR:-/srv/card-catalog}
grafana=${GRAFANA_URL:-http://localhost:3000}
auth=${GRAFANA_AUTH:-admin:admin}
out="$dir/evidence"; mkdir -p "$out"
now=$(date +%s); start=$((now - 15 * 60)); range_start=$((now - 30 * 60))
manifest=()

record() { manifest+=("$(jq -cn --arg f "$1" --arg s "$2" --arg d "$3" '{file:$f, status:$s, what:$d}')"); }

q() { # <file> <description> <grafana path> [curl --data-urlencode args...]
  local file=$1 what=$2 path=$3; shift 3
  if curl -sfS -G -u "$auth" --max-time 15 "$grafana$path" "$@" | jq . > "$out/$file" 2> /dev/null; then
    record "$file" ok "$what"
  else
    echo '{"error":"query failed"}' > "$out/$file"; record "$file" failed "$what"
  fi
}

prom=/api/datasources/proxy/uid/prometheus/api/v1
sel="job=\"card-catalog\",deployment_environment_name=\"$env\""

# --- Deploy state: what runs now, what ran before, what changed -----------
var=$([[ $env == prod ]] && echo PROD || echo STAGING)
current=$(grep -E "^${var}_IMAGE=" "$srv/images.env" | cut -d= -f2-)
previous=$(grep -E "^${var}_PREVIOUS_IMAGE=" "$srv/images.env" | cut -d= -f2-)
container=$(docker ps -q --filter "label=com.docker.compose.project=card-catalog" --filter "label=com.docker.compose.service=$env" | head -1)
started=$([[ -n $container ]] && docker inspect -f '{{.State.StartedAt}}' "$container" || echo "")
commit_of() { local t=${1##*:}; [[ $t =~ ^[0-9a-f]{7,40}$ ]] && echo "$t" || echo ""; }
cur_sha=$(commit_of "$current"); prev_sha=$(commit_of "$previous")
describe() { # commit summary if this checkout has it
  [[ -n $1 ]] && git -C "$repo" cat-file -e "$1^{commit}" 2> /dev/null &&
    git -C "$repo" show -s --format='%H%n%an, %ad%n%s%n%n%b' --date=iso "$1" || echo "(commit not in this checkout)"
}
jq -n --arg env "$env" --arg current "$current" --arg previous "$previous" --arg started "$started" \
  --arg cur_sha "$cur_sha" --arg prev_sha "$prev_sha" \
  --arg cur_commit "$(describe "$cur_sha")" --arg prev_commit "$(describe "$prev_sha")" \
  '{environment:$env, current_image:$current, previous_image:$previous, container_started_at:$started,
    current_commit:{sha:$cur_sha, summary:$cur_commit}, previous_commit:{sha:$prev_sha, summary:$prev_commit}}' \
  > "$out/deploy.json"
record deploy.json ok "current and previous image, container start time, commit summaries"

if [[ -n $cur_sha && -n $prev_sha ]] && git -C "$repo" cat-file -e "$cur_sha^{commit}" 2> /dev/null &&
   git -C "$repo" cat-file -e "$prev_sha^{commit}" 2> /dev/null; then
  { git -C "$repo" log --oneline "$prev_sha..$cur_sha"; echo; git -C "$repo" diff --stat "$prev_sha" "$cur_sha" -- 05-final-project/backend 05-final-project/frontend; echo
    git -C "$repo" diff "$prev_sha" "$cur_sha" -- 05-final-project/backend/app | head -400; } > "$out/change.diff"
  record change.diff ok "commits, file stats and app diff between the previous and current image"
else
  echo "(no diff: one of the commits is not in this checkout)" > "$out/change.diff"
  record change.diff partial "commits not available locally"
fi

# --- Metrics -------------------------------------------------------------
q metrics-5xx.json "5xx in the last 15 minutes by route and image" "$prom/query" \
  --data-urlencode "query=sum by (http_route, http_request_method, service_version) (increase(http_server_request_duration_seconds_count{$sel,http_response_status_code=~\"5..\"}[15m]))"
q metrics-requests.json "all requests in the last 15 minutes by route and status" "$prom/query" \
  --data-urlencode "query=sum by (http_route, http_request_method, http_response_status_code) (increase(http_server_request_duration_seconds_count{$sel}[15m]))"
q metrics-5xx-timeline.json "5xx per minute over the last 30 minutes, by image" "$prom/query_range" \
  --data-urlencode "query=sum by (service_version) (increase(http_server_request_duration_seconds_count{$sel,http_response_status_code=~\"5..\"}[1m]))" \
  --data-urlencode "start=$range_start" --data-urlencode "end=$now" --data-urlencode "step=60"

# --- Logs: unhandled exceptions with stack traces -------------------------
q logs-errors.json "ERROR logs (unhandled exceptions) in the last 15 minutes" \
  /api/datasources/proxy/uid/loki/loki/api/v1/query_range \
  --data-urlencode "query={service_name=\"card-catalog\"} | deployment_environment_name=\"$env\" | severity_text=\"ERROR\"" \
  --data-urlencode "start=${start}000000000" --data-urlencode "end=${now}000000000" --data-urlencode "limit=20"

# --- Traces: the failing requests ------------------------------------------
tempo=/api/datasources/proxy/uid/tempo/api
q traces-search.json "error traces in the last 15 minutes" "$tempo/search" \
  --data-urlencode "q={ resource.service.name = \"card-catalog\" && resource.deployment.environment.name = \"$env\" && status = error }" \
  --data-urlencode "start=$start" --data-urlencode "end=$now" --data-urlencode "limit=5"
for id in $(jq -r '.traces[]?.traceID' "$out/traces-search.json" 2> /dev/null | head -3); do
  [[ $id =~ ^[0-9a-f]+$ ]] && q "trace-$id.json" "full trace $id" "$tempo/traces/$id"
done

# --- The container's own output ---------------------------------------------
if [[ -n $container ]]; then
  docker logs --since 15m --tail 200 "$container" > "$out/container.log" 2>&1
  record container.log ok "last 200 lines of the $env container's output (15 min)"
fi

# --- What the front door says right now --------------------------------------
host=$([[ $env == prod ]] && echo cards.terzotech.net || echo staging.cards.terzotech.net)
if "$srv/smoke.sh" "https://$host" --local > "$out/smoke-now.txt" 2>&1; then
  record smoke-now.txt ok "smoke test now: passed"
else
  record smoke-now.txt ok "smoke test now: FAILED"
fi

# --- Redact client IP addresses ----------------------------------------------
# Incident folders are committed to a public repository and read by a model:
# replace every public IPv4 address (visitors, the owner) with a placeholder.
# Private and loopback addresses (containers, the host) stay; they help.
python3 - "$out" <<'PY'
import ipaddress, pathlib, re, sys
ip = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{1,3}){3})(?![\d.])")
def scrub(m):
    try:
        a = ipaddress.ip_address(m.group(1))
    except ValueError:
        return m.group(1)
    return m.group(1) if (a.is_private or a.is_loopback) else "<public-ip>"
for f in pathlib.Path(sys.argv[1]).iterdir():
    f.write_text(ip.sub(scrub, f.read_text(errors="replace")))
PY
record redaction ok "public IPv4 addresses replaced with <public-ip> in every evidence file"

printf '%s\n' "${manifest[@]}" | jq -s --arg env "$env" --arg route "$route" --arg at "$(date -u +%FT%TZ)" \
  '{collected_at:$at, environment:$env, route:$route, files:.}' > "$out/manifest.json"
echo "evidence: $(jq '.files | length' "$out/manifest.json") files in $out"
