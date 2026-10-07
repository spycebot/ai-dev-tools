#!/usr/bin/env bash
# Run deploy.sh on the EC2 host through AWS Systems Manager, from GitHub Actions.
#
#   ssm-run.sh <commit-sha> deploy   <staging|prod> <image>
#   ssm-run.sh <commit-sha> rollback <staging|prod>
#
# Needs AWS credentials (deploy.yml gets short-lived ones via OIDC) and
# INSTANCE_ID in the environment. The remote side first syncs the deploy/
# files from this exact commit into /srv/card-catalog (env files and
# images.env are never touched), then runs deploy.sh as the `ubuntu` user.
# Prints the remote output and exits non-zero if the remote command failed.
set -euo pipefail

sha=${1:?commit sha}; shift
: "${INSTANCE_ID:?set INSTANCE_ID}"
repo=${GITHUB_REPOSITORY:-spycebot/ai-dev-tools}
raw="https://raw.githubusercontent.com/$repo/$sha/03-test-containerize-and-deploy-an-ai-assisted-app/deploy"

# Arguments are validated here, so nothing user-controlled is spliced into
# the remote shell beyond these fixed shapes.
[[ $sha =~ ^[0-9a-f]{40}$ ]] || { echo "bad sha: $sha" >&2; exit 2; }
for a in "$@"; do
  [[ $a =~ ^[A-Za-z0-9._:/@-]+$ ]] || { echo "bad argument: $a" >&2; exit 2; }
done

remote=$(cat <<EOF
set -euo pipefail
cd /srv/card-catalog
for f in docker-compose.server.yml Caddyfile deploy.sh smoke.sh set-password.sh; do
  curl -fsSL --retry 3 "$raw/\$f" -o "\$f.new"
done
caddy_changed=0
cmp -s Caddyfile.new Caddyfile || caddy_changed=1
for f in docker-compose.server.yml Caddyfile deploy.sh smoke.sh set-password.sh; do
  cat "\$f.new" > "\$f" && rm "\$f.new"   # rewrite in place: Caddyfile is bind-mounted
done
chown ubuntu:ubuntu *; chmod 755 *.sh
sudo -u ubuntu -H ./deploy.sh $*
if [ "\$caddy_changed" = 1 ]; then
  sudo -u ubuntu docker compose --env-file images.env -f docker-compose.server.yml exec -T caddy caddy reload --config /etc/caddy/Caddyfile
fi
EOF
)

params=$(python3 -c 'import json,sys; print(json.dumps({"commands": [sys.stdin.read()], "executionTimeout": ["900"]}))' <<< "$remote")
cmd_id=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name AWS-RunShellScript \
  --comment "card-catalog $* @ ${sha:0:7}" \
  --parameters "$params" \
  --query Command.CommandId --output text)
echo "SSM command $cmd_id: deploy.sh $*"

# Poll until the command finishes (get-command-invocation can briefly 404
# right after send-command, hence the || true).
status=Pending
for _ in $(seq 1 180); do
  sleep 5
  status=$(aws ssm get-command-invocation --command-id "$cmd_id" --instance-id "$INSTANCE_ID" \
    --query Status --output text 2>/dev/null || echo Pending)
  case $status in Pending|InProgress|Delayed) continue ;; *) break ;; esac
done

aws ssm get-command-invocation --command-id "$cmd_id" --instance-id "$INSTANCE_ID" \
  --query '[StandardOutputContent, StandardErrorContent]' --output text
echo "SSM status: $status"
[[ $status == Success ]]
