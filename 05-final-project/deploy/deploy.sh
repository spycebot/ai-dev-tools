#!/usr/bin/env bash
# Deploy (or roll back) one Card Catalog environment on the EC2 host.
#
#   deploy.sh deploy   <staging|prod> <image>   verify, migrate, switch, smoke test;
#                                               auto-rollback if the smoke test fails
#   deploy.sh rollback <staging|prod>           switch back to the previous image
#   deploy.sh verify   <image>                  only the image check below
#   deploy.sh status                            show what each environment runs
#
# Runs in /srv/card-catalog (see docker-compose.server.yml). images.env keeps
# the current and previous image for each environment, so a rollback is a
# redeploy of a known-good image, not a rebuild. Migrations are never rolled
# back: they must stay backward compatible (see docs/release-process.md).
#
# Only images the deploy workflow built are deployed (audit F18): the image
# must be ghcr.io/spycebot/card-catalog:<full commit sha>, pullable from the
# registry (so not a local build), and labelled with that same commit. Only
# the workflow's build job pushes there, and it runs only after CI passes on
# main. For a game day, ALLOW_UNVERIFIED_IMAGE=1 lets a local image onto
# staging, never prod. Staging deploys also run a write smoke test (create,
# move to the end of a column, delete) inside the new container.
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

# Staging only: it writes (one card, deleted again). Not run on rollback,
# because images from before this check don't contain the script.
smoke_write() { [[ $1 != staging ]] || "${COMPOSE[@]}" exec -T "$1" python -m scripts.smoke_write; }

REGISTRY_IMAGE=ghcr.io/spycebot/card-catalog
verify_image() { # <image>
  local image=$1 sha revision
  local pattern='^ghcr\.io/spycebot/card-catalog:([0-9a-f]{40})$'
  [[ $image =~ $pattern ]] ||
    { echo "refusing $image: not $REGISTRY_IMAGE:<full commit sha>" >&2; return 1; }
  sha=${BASH_REMATCH[1]}
  docker pull -q "$image" >/dev/null ||
    { echo "refusing $image: not in the registry, so not built by the deploy workflow" >&2; return 1; }
  revision=$(docker image inspect -f '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$image")
  [[ $revision == "$sha" ]] ||
    { echo "refusing $image: labelled with commit '$revision', not $sha" >&2; return 1; }
  echo "==> verified $image (registry, commit label)"
}

cmd=${1:-}
case $cmd in
  deploy)
    env=${2:?env}; image=${3:?image}; v=$(var_for "$env")
    [[ $env == prod || $env == staging ]] || { echo "env must be prod or staging" >&2; exit 2; }
    current=$(get "${v}_IMAGE")
    echo "==> $env: $current -> $image"

    if ! verify_image "$image"; then
      if [[ ${ALLOW_UNVERIFIED_IMAGE:-} == 1 && $env == staging ]] && docker image inspect "$image" >/dev/null; then
        echo "==> WARNING: deploying an unverified image to staging (ALLOW_UNVERIFIED_IMAGE=1)" >&2
      else
        exit 1
      fi
    fi

    echo "==> $env: alembic upgrade head"
    env "${v}_IMAGE=$image" "${COMPOSE[@]}" run --rm --no-deps "$env" alembic upgrade head

    echo "==> $env: switching containers"
    if switch_to "$env" "$image" && smoke "$env" && smoke_write "$env"; then
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
  verify)
    verify_image "${2:?image}"
    ;;
  status)
    cat images.env
    "${COMPOSE[@]}" ps
    ;;
  *)
    sed -n '2,8p' "$0"; exit 2 ;;
esac
