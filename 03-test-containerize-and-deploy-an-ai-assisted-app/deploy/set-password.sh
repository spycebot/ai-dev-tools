#!/usr/bin/env bash
# Set (or rotate) the login password for one or both deployed environments.
#
#   /srv/card-catalog/set-password.sh            # both prod and staging
#   /srv/card-catalog/set-password.sh staging    # just one
#
# Prompts without echoing, hashes with bcrypt inside the app image, and writes
# only the hash into <env>.env — the plaintext never touches disk or a log.
# Restarts the affected app containers so the new hash takes effect.
set -euo pipefail
cd "$(dirname "$0")"

envs=("${@:-prod staging}"); read -ra envs <<< "${envs[*]}"
image=$(grep -E '^(PROD|STAGING)_IMAGE=' images.env | head -1 | cut -d= -f2-)

hash=$(docker run --rm -i "$image" python -c '
import bcrypt, getpass, sys
p = getpass.getpass("New password: ", stream=sys.stderr)
if p != getpass.getpass("Confirm password: ", stream=sys.stderr):
    sys.exit("Passwords did not match; nothing changed.")
if len(p) < 12:
    sys.exit("Use at least 12 characters for a public deployment.")
print(bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode())
' < /dev/tty)

for env in "${envs[@]}"; do
  f="$env.env"
  [[ -f $f ]] || { echo "$f not found" >&2; exit 1; }
  # Single quotes: Compose would otherwise expand the `$` in a bcrypt hash.
  sed -i "/^AUTH_PASSWORD_HASH=/d" "$f"
  echo "AUTH_PASSWORD_HASH='$hash'" >> "$f"
  echo "updated $f"
done

if docker compose --env-file images.env -f docker-compose.server.yml ps -q "${envs[@]}" 2>/dev/null | grep -q .; then
  docker compose --env-file images.env -f docker-compose.server.yml up -d --force-recreate --no-deps "${envs[@]}"
fi
