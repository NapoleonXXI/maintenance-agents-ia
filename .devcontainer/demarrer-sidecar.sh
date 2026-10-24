#!/usr/bin/env bash
# Prépare la base (au premier lancement) puis démarre le sidecar sur le port 8810.
cd "$(dirname "$0")/.."
if [ "$1" = "init" ] || [ ! -f maintenance.db ]; then python3 orchestrator.py --reset > /dev/null; fi
[ "$1" = "init" ] && exit 0
pkill -f sidecar.py 2>/dev/null
PORT=8810 nohup python3 sidecar.py > sidecar.log 2>&1 &
echo "Sidecar démarré sur le port 8810"
