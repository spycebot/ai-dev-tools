#!/usr/bin/env bash
# Runbook: decide whether an environment has recovered after an action.
#
#   runbooks/verify-recovery.sh <prod|staging> <expected-image> [watch-seconds]
#
# Recovered means all of:
#   1. the environment runs the expected image (the rollback really happened)
#   2. its container reports healthy
#   3. the smoke test passes through the real HTTPS front door
#   4. Prometheus sees no new 5xx from that environment for watch-seconds
#      (default 180) after the check starts
# Prints one JSON object (the verification record) and exits 0 only if all pass.
set -uo pipefail

env=${1:?env}; expected=${2:?expected image}; watch=${3:-180}
[[ $env == prod || $env == staging ]] || { echo "environment must be prod or staging" >&2; exit 2; }
srv=${SRV_DIR:-/srv/card-catalog}
grafana=${GRAFANA_URL:-http://localhost:3000}; auth=${GRAFANA_AUTH:-admin:admin}
var=$([[ $env == prod ]] && echo PROD || echo STAGING)
host=$([[ $env == prod ]] && echo cards.terzotech.net || echo staging.cards.terzotech.net)
started=$(date -u +%FT%TZ)

running=$(grep -E "^${var}_IMAGE=" "$srv/images.env" | cut -d= -f2-)
image_ok=$([[ $running == "$expected" ]] && echo true || echo false)

container=$(docker ps -q --filter "label=com.docker.compose.project=card-catalog" --filter "label=com.docker.compose.service=$env" | head -1)
health=$([[ -n $container ]] && docker inspect -f '{{.State.Health.Status}}' "$container" || echo missing)

smoke_ok=true; smoke=$("$srv/smoke.sh" "https://$host" --local 2>&1) || smoke_ok=false

errors() { # 5xx from this environment since the check started
  curl -sfS -G -u "$auth" --max-time 15 "$grafana/api/datasources/proxy/uid/prometheus/api/v1/query" \
    --data-urlencode "query=sum(increase(http_server_request_duration_seconds_count{job=\"card-catalog\",deployment_environment_name=\"$env\",http_response_status_code=~\"5..\"}[${1}s]))" |
    jq -r '.data.result[0].value[1] // "0"' 2> /dev/null || echo unknown
}
sleep "$watch"
new_5xx=$(errors "$watch")
errors_ok=$([[ $new_5xx != unknown ]] && awk "BEGIN{exit !($new_5xx < 0.5)}" && echo true || echo false)

recovered=false
[[ $image_ok == true && $health == healthy && $smoke_ok == true && $errors_ok == true ]] && recovered=true
jq -n --arg env "$env" --arg expected "$expected" --arg running "$running" --arg health "$health" \
  --arg smoke "$smoke" --arg new_5xx "$new_5xx" --arg started "$started" --arg ended "$(date -u +%FT%TZ)" \
  --argjson watch "$watch" --argjson image_ok "$image_ok" --argjson smoke_ok "$smoke_ok" \
  --argjson errors_ok "$errors_ok" --argjson recovered "$recovered" \
  '{environment:$env, started_at:$started, ended_at:$ended, recovered:$recovered,
    checks:{image:{ok:$image_ok, expected:$expected, running:$running},
            container_health:{ok:($health=="healthy"), status:$health},
            smoke_test:{ok:$smoke_ok, output:$smoke},
            no_new_5xx:{ok:$errors_ok, window_seconds:$watch, count:$new_5xx}}}'
[[ $recovered == true ]]
