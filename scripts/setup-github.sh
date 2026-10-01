#!/usr/bin/env bash
# Interactively sets GitHub Actions variables and secrets for me-hub.
# Usage: scripts/setup-github.sh [owner/repo]
# Requires: gh (authenticated, admin access to the repository), openssl, ssh-keygen, ssh-keyscan.
set -euo pipefail

readonly DEFAULT_TIMEZONE="Asia/Dubai"
readonly DEFAULT_REMINDER_TIME="23:00"
readonly DEFAULT_MORNING_REMINDER_TIME="09:00"
readonly DEFAULT_DEPLOY_PATH="/opt/me-hub"
readonly DEFAULT_SSH_KEY_PATH="$HOME/.ssh/me-hub-deploy"

REPO=""
EXISTING_SECRETS=""
CHANGED=()

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '\n\033[1m%s\033[0m\n' "$*"
}

confirm() {
  local prompt=$1 default=$2 answer
  read -r -p "$prompt " answer
  answer=${answer:-$default}
  [[ $answer =~ ^[Yy]([Ee][Ss])?$ ]]
}

check_prerequisites() {
  local tool
  for tool in gh openssl ssh-keygen ssh-keyscan; do
    command -v "$tool" >/dev/null 2>&1 || die "'$tool' is not installed"
  done
  gh auth status >/dev/null 2>&1 || die "gh is not authenticated; run 'gh auth login'"
}

resolve_repo() {
  REPO=${1:-$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)}
  [[ $REPO =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || die "Cannot determine repository; pass it as owner/repo"
  [[ $(gh api "repos/$REPO" --jq .permissions.admin 2>/dev/null) == "true" ]] \
    || die "You need admin access to $REPO to manage Actions variables and secrets"
  EXISTING_SECRETS=$(gh secret list --repo "$REPO" --json name --jq '.[].name')
}

secret_exists() {
  grep -qxF "$1" <<<"$EXISTING_SECRETS"
}

current_variable() {
  gh variable get "$1" --repo "$REPO" 2>/dev/null || true
}

is_positive_int() { [[ $1 =~ ^[1-9][0-9]{0,19}$ ]]; }
is_bot_username() { [[ $1 =~ ^[A-Za-z][A-Za-z0-9_]{3,30}[Bb][Oo][Tt]$ ]]; }
is_hh_mm() { [[ $1 =~ ^([01][0-9]|2[0-3]):[0-5][0-9]$ ]]; }
is_hostname() { [[ $1 =~ ^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$ ]]; }
is_unix_user() { [[ $1 =~ ^[a-z_][a-z0-9_-]{0,31}$ ]]; }
is_absolute_path() { [[ $1 =~ ^/[A-Za-z0-9._/-]*$ ]]; }
is_bot_token() { [[ $1 =~ ^[0-9]{5,20}:[A-Za-z0-9_-]{30,}$ ]]; }

is_timezone() {
  [[ $1 =~ ^[A-Za-z]+(/[A-Za-z0-9_+-]+)*$ ]] || return 1
  [[ ! -d /usr/share/zoneinfo ]] || [[ -f /usr/share/zoneinfo/$1 ]]
}

# prompt_variable NAME DESCRIPTION VALIDATOR [DEFAULT]
prompt_variable() {
  local name=$1 description=$2 validator=$3 fallback=${4:-} current value
  current=$(current_variable "$name")
  local default=${current:-$fallback}
  while true; do
    read -r -p "$description${default:+ [$default]}: " value
    value=${value:-$default}
    value=${value#@}
    if [[ -z $value ]]; then
      echo "  A value is required."
    elif ! "$validator" "$value"; then
      echo "  Invalid value, try again."
    else
      break
    fi
  done
  if [[ $value != "$current" ]]; then
    gh variable set "$name" --repo "$REPO" --body "$value" >/dev/null
    CHANGED+=("variable $name")
  fi
}

# prompt_secret NAME DESCRIPTION VALIDATOR
prompt_secret() {
  local name=$1 description=$2 validator=$3 value hint=""
  secret_exists "$name" && hint=" (leave empty to keep the current value)"
  while true; do
    read -r -s -p "$description$hint: " value
    echo
    if [[ -z $value ]] && secret_exists "$name"; then
      return
    elif [[ -z $value ]]; then
      echo "  A value is required."
    elif ! "$validator" "$value"; then
      echo "  Invalid value, try again."
    else
      break
    fi
  done
  printf '%s' "$value" | gh secret set "$name" --repo "$REPO" >/dev/null
  CHANGED+=("secret $name")
}

setup_session_secret() {
  if secret_exists SESSION_SECRET && ! confirm "Regenerate SESSION_SECRET? This signs out the web dashboard. [y/N]" n; then
    return
  fi
  openssl rand -hex 32 | tr -d '\n' | gh secret set SESSION_SECRET --repo "$REPO" >/dev/null
  CHANGED+=("secret SESSION_SECRET (generated)")
}

setup_application() {
  info "Telegram bot"
  prompt_secret TELEGRAM_BOT_TOKEN "Bot token from @BotFather" is_bot_token
  prompt_variable TELEGRAM_BOT_USERNAME "Bot username (without @)" is_bot_username
  prompt_variable TELEGRAM_OWNER_ID "Your Telegram user id (ask @userinfobot)" is_positive_int

  info "Reminders"
  prompt_variable DEFAULT_TIMEZONE "Default timezone (IANA)" is_timezone "$DEFAULT_TIMEZONE"
  prompt_variable DEFAULT_REMINDER_TIME "Evening check-in time, HH:MM" is_hh_mm "$DEFAULT_REMINDER_TIME"
  prompt_variable MORNING_REMINDER_TIME "Morning reminder time, HH:MM" is_hh_mm "$DEFAULT_MORNING_REMINDER_TIME"

  info "Web dashboard"
  setup_session_secret
}

setup_ssh_key() {
  local key_path
  if secret_exists DEPLOY_SSH_KEY && ! confirm "Replace DEPLOY_SSH_KEY? [y/N]" n; then
    return
  fi
  read -r -p "Path to the deploy private key [$DEFAULT_SSH_KEY_PATH]: " key_path
  key_path=${key_path:-$DEFAULT_SSH_KEY_PATH}
  key_path=${key_path/#\~/$HOME}
  if [[ ! -f $key_path ]]; then
    confirm "No key at $key_path. Generate a new ed25519 key? [Y/n]" y || die "A deploy key is required"
    mkdir -p "$(dirname "$key_path")"
    ssh-keygen -t ed25519 -N "" -C "me-hub-deploy@github-actions" -f "$key_path" >/dev/null
    echo "  Add this public key to ~/.ssh/authorized_keys of the deploy user on the server:"
    echo "  $(cat "$key_path.pub")"
  fi
  ssh-keygen -y -P "" -f "$key_path" >/dev/null 2>&1 \
    || die "$key_path is not a readable private key without a passphrase"
  gh secret set DEPLOY_SSH_KEY --repo "$REPO" <"$key_path" >/dev/null
  CHANGED+=("secret DEPLOY_SSH_KEY")
}

setup_known_hosts() {
  local host=$1 keys
  if [[ -n $(current_variable SSH_KNOWN_HOSTS) ]] && ! confirm "Refresh SSH_KNOWN_HOSTS for $host? [y/N]" n; then
    return
  fi
  keys=$(ssh-keyscan -T 10 "$host" 2>/dev/null) || true
  [[ -n $keys ]] || die "ssh-keyscan could not reach $host"
  echo "  Host key fingerprints of $host:"
  ssh-keygen -lf - <<<"$keys" | sed 's/^/    /'
  confirm "Do they match the server (check with 'ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub')? [y/N]" n \
    || die "Host keys not confirmed"
  gh variable set SSH_KNOWN_HOSTS --repo "$REPO" --body "$keys" >/dev/null
  CHANGED+=("variable SSH_KNOWN_HOSTS")
}

setup_deploy() {
  info "Deploy over SSH"
  confirm "Configure deploy variables and the SSH key? [y/N]" n || return 0
  prompt_variable DEPLOY_HOST "Server hostname or IP" is_hostname
  prompt_variable DEPLOY_USER "SSH user" is_unix_user
  prompt_variable DEPLOY_PATH "Project directory on the server" is_absolute_path "$DEFAULT_DEPLOY_PATH"
  setup_known_hosts "$(current_variable DEPLOY_HOST)"
  setup_ssh_key
}

main() {
  check_prerequisites
  resolve_repo "${1:-}"
  echo "Configuring GitHub Actions for $REPO"
  setup_application
  setup_deploy

  info "Done"
  if ((${#CHANGED[@]} == 0)); then
    echo "Nothing changed."
  else
    printf '  updated %s\n' "${CHANGED[@]}"
  fi
}

main "$@"
