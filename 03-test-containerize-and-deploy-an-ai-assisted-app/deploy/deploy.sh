#!/usr/bin/env bash
# Deploy (or roll back) one Card Catalog environment on the EC2 host.
#
#   deploy.sh deploy   <staging|prod> <image>   migrate, switch, smoke test;
#                                               auto-rollback if the smoke test fails
#   deploy.sh rollback <staging|prod>           switch back to the previous image
#   deploy.sh status                            show what each environment runs
#
# Runs in /srv/card-catalog (see docker-compose.server.yml). images.env keeps
# the current and previous image for each environment, so a rollback is a
# redeploy of a known-good image, not a rebuild. Migrations are never rolled
# back: they must stay backward compatible (see docs/release-process.md).
set -euo pipefail

cd "$(dirname "$0")"
COMPOSE=(docker compose --env-file images.env -f docker-compose.server.yml)

host_for() { [[ $1 == prod ]] && echo cards.terzotech.net || echo staging.cards.terzotech.net; }
var_for() { [[ $1 == prod ]] && echo PROD || echo STAGING; }

get() { grep -E "^$1=" images.env 2>/dev/null | cut -d= -f2- || true; }
set_var() {
  touch images.env
  if grep -qE "^$1=" images.env; then sed -i "s|^$1=.*|$1=$2|" images.env
  else echo "$1=$2" >> images.env; fi
}

switch_to() { # <env> <image>
  local env=$1 image=$2 v; v=$(var_for "$env")
  set_var "${v}_IMAGE" "$image"
  "${COMPOSE[@]}" up -d --no-deps "$env"
  "${COMPOSE[@]}" up -d caddy
  # Wait for the container's own HEALTHCHECK (Dockerfile) to pass.
  local id; id=$("${COMPOSE[@]}" ps -q "$env")
  for _ in $(seq 1 30); do
    case $(docker inspect -f '{{.State.Health.Status}}' "$id") in
      healthy) return 0 ;;
      unhealthy) break ;;
    esac
    sleep 2
  done
  echo "container for $env did not become healthy" >&2
  "${COMPOSE[@]}" logs --tail 50 "$env" >&2
  return 1
}

smoke() { ./smoke.sh "https://$(host_for "$1")" --local; }

cmd=${1:-}
case $cmd in
  deploy)
    env=${2:?env}; image=${3:?image}; v=$(var_for "$env")
    [[ $env == prod || $env == staging ]] || { echo "env must be prod or staging" >&2; exit 2; }
    current=$(get "${v}_IMAGE")
    echo "==> $env: $current -> $image"

    docker pull -q "$image" || docker image inspect "$image" >/dev/null

    echo "==> $env: alembic upgrade head"
    env "${v}_IMAGE=$image" "${COMPOSE[@]}" run --rm --no-deps "$env" alembic upgrade head

    echo "==> $env: switching containers"
    if switch_to "$env" "$image" && smoke "$env"; then
      [[ -n $current && $current != "$image" ]] && set_var "${v}_PREVIOUS_IMAGE" "$current"
      echo "==> $env: deployed $image"
      docker image prune -f >/dev/null
    else
      echo "==> $env: DEPLOY FAILED — rolling back to $current" >&2
      if [[ -n $current ]]; then
        switch_to "$env" "$current" && smoke "$env" && echo "==> $env: rolled back to $current" >&2
      fi
      exit 1
    fi
    ;;
  rollback)
    env=${2:?env}; v=$(var_for "$env")
    previous=$(get "${v}_PREVIOUS_IMAGE")
    [[ -n $previous ]] || { echo "no previous image recorded for $env" >&2; exit 1; }
    current=$(get "${v}_IMAGE")
    echo "==> $env: rolling back $current -> $previous"
    switch_to "$env" "$previous"
    smoke "$env"
    set_var "${v}_PREVIOUS_IMAGE" "$current"
    echo "==> $env: now running $previous (run rollback again to undo)"
    ;;
  status)
    cat images.env
    "${COMPOSE[@]}" ps
    ;;
  *)
    sed -n '2,12p' "$0"; exit 2 ;;
esac
