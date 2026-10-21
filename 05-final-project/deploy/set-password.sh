#!/usr/bin/env bash
# Set (or rotate) the login password for one or both deployed environments.
#
#   /srv/card-catalog/set-password.sh            # both prod and staging
#   /srv/card-catalog/set-password.sh staging    # just one
#
# Prompts without echoing, hashes with bcrypt inside the app image, and writes
# only the hash into <env>.env — the plaintext never touches disk or a log.
# Also replaces AUTH_SECRET_KEY (a new random key per environment), which
# invalidates every existing session: a password reset signs every browser
# out, including one holding a stolen cookie (security audit F07).
# Restarts the affected app containers so the new hash and key take effect.
set -euo pipefail
cd "$(dirname "$0")"

envs=("${@:-prod staging}"); read -ra envs <<< "${envs[*]}"
image=$(grep -E '^(PROD|STAGING)_IMAGE=' images.env | head -1 | cut -d= -f2-)

# The container has no terminal of its own (`-i`, no `-t`, so the hash comes
# back cleanly on stdout), so echo is turned off on ours instead, and always
# turned back on. The prompts go to stderr.
stty -echo < /dev/tty
trap 'stty echo < /dev/tty' EXIT
hash=$(docker run --rm -i "$image" python -c '
import bcrypt, sys
def ask(prompt):
    print(prompt, end="", file=sys.stderr, flush=True)
    line = sys.stdin.readline().rstrip("\n")
    print(file=sys.stderr)
    return line
p = ask("New password: ")
if p != ask("Confirm password: "):
    sys.exit("Passwords did not match; nothing changed.")
if len(p) < 12:
    sys.exit("Use at least 12 characters for a public deployment.")
print(bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode())
' < /dev/tty)
stty echo < /dev/tty

for env in "${envs[@]}"; do
  f="$env.env"
  [[ -f $f ]] || { echo "$f not found" >&2; exit 1; }
  # Single quotes: Compose would otherwise expand the `$` in a bcrypt hash.
  sed -i "/^AUTH_PASSWORD_HASH=/d; /^AUTH_SECRET_KEY=/d" "$f"
  echo "AUTH_PASSWORD_HASH='$hash'" >> "$f"
  # A different signing key per environment, so a staging cookie is never
  # valid in production.
  echo "AUTH_SECRET_KEY=$(openssl rand -hex 32)" >> "$f"
  echo "updated $f (new password hash and session key; existing sessions end)"
done

if docker compose --env-file images.env -f docker-compose.server.yml ps -q "${envs[@]}" 2>/dev/null | grep -q .; then
  docker compose --env-file images.env -f docker-compose.server.yml up -d --force-recreate --no-deps "${envs[@]}"
fi
