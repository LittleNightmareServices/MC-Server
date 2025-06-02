#!/bin/bash
set -x
cd "$(dirname "$0")"
echo 'Dummy Server Script Starting...'
trap 'echo "[DUMMY app.py] SIGTERM received, stopping."; exit 0' SIGTERM
echo 'Entering command loop...'
while true; do
  read -r cmd
  if [ -n "$cmd" ]; then
    echo "CMD_RECEIVED: $cmd"
  fi
  if [ "$cmd" == "stop" ]; then
    echo 'STOP_CMD_RECEIVED. Exiting.'
    exit 0
  fi
  sleep 0.1
done
