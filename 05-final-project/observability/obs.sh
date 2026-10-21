#!/usr/bin/env bash
# Start or stop Card Catalog's monitoring stack on the EC2 host.
#
#   observability/obs.sh up       start the stack, then switch the app's OTLP export on
#   observability/obs.sh down     switch export off, then stop the stack (data volumes kept)
#   observability/obs.sh status   what's running, and whether export is on
#
# Export is switched by the presence of /srv/card-catalog/observability.env,
# which docker-compose.server.yml loads into the prod and staging containers
# if it exists. Switching recreates both app containers: each is unavailable
# for a few seconds. Run from the repo checkout on the server.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
srv=/srv/card-catalog
stack=(docker compose -f "$here/compose.yaml")
app=(docker compose --project-directory "$srv" --env-file "$srv/images.env" -f "$srv/docker-compose.server.yml")

recreate_apps() {
  "${app[@]}" up -d --no-deps --force-recreate --wait prod staging
}

case ${1:-} in
  up)
    "${stack[@]}" up -d --wait
    install -m 644 "$here/observability.env" "$srv/observability.env"
    recreate_apps
    echo "monitoring up; app export on. Grafana: ssh -L 3000:localhost:3000 <host>, then http://localhost:3000"
    ;;
  down)
    rm -f "$srv/observability.env"
    recreate_apps
    "${stack[@]}" down
    echo "app export off; monitoring stopped (volumes kept; 'docker volume ls | grep card-catalog-obs')"
    ;;
  status)
    "${stack[@]}" ps --format 'table {{.Service}}\t{{.Status}}'
    [[ -f $srv/observability.env ]] && echo "app export: on" || echo "app export: off"
    ;;
  *)
    sed -n '2,10p' "$0" >&2
    exit 2
    ;;
esac
