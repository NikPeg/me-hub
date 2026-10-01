#!/usr/bin/env bash
set -euo pipefail

deploy_path=${1:?Usage: deploy.sh DEPLOY_PATH}
[[ $deploy_path =~ ^/[A-Za-z0-9._/-]+$ ]] || { echo "Invalid deploy path" >&2; exit 1; }
[[ $(id -u) -eq 0 ]] || { echo "Deployment requires root" >&2; exit 1; }

cd "$deploy_path"
test -s .env.runtime

docker compose build migrate
docker compose run --rm migrate
docker compose up -d --force-recreate bot web

install -d -m 755 /var/www/me-hub
rsync -a --delete web/ /var/www/me-hub/
install -m 644 nginx/me-hub.conf /etc/nginx/sites-available/me-hub
ln -sfn /etc/nginx/sites-available/me-hub /etc/nginx/sites-enabled/me-hub
nginx -t
systemctl reload nginx

for attempt in {1..30}; do
  if curl --fail --silent --output /dev/null http://127.0.0.1:8000/api/config; then
    break
  fi
  if [[ $attempt -eq 30 ]]; then
    docker compose logs --tail=100 web
    echo "Web API did not become ready" >&2
    exit 1
  fi
  sleep 2
done

curl --fail --silent --show-error --insecure --output /dev/null \
  --resolve me.nikpeg.me:443:127.0.0.1 https://me.nikpeg.me/
curl --fail --silent --show-error --insecure --output /dev/null \
  --resolve me.nikpeg.me:443:127.0.0.1 https://me.nikpeg.me/api/config
docker compose ps
