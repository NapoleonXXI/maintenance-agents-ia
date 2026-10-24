#!/usr/bin/env bash
# init : installe Rails (gems dans pilote/vendor/bundle) et prépare la base. Sinon : démarre Pilote sur le port 8810.
cd "$(dirname "$0")/.."
if [ "$1" = "init" ]; then
  (cd pilote && bundle config set --local path vendor/bundle && bundle install)
fi
[ -f maintenance.db ] || python3 orchestrator.py --reset > /dev/null
[ "$1" = "init" ] && exit 0
pkill -f "puma.*8810" 2>/dev/null; rm -f pilote/tmp/pids/server.pid
(cd pilote && nohup bin/rails server -b 0.0.0.0 -p 8810 > log/serveur.log 2>&1 &)
echo "Pilote démarré sur le port 8810"
