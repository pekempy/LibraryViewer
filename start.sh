#!/bin/bash

echo "Starting fetch_and_build loop..."

# Background loop: re-fetch every 1 hour
while true; do
  echo "Running fetch_and_build.py at $(date)"
  python3 /app/fetch_and_build.py

  echo "Copying output to nginx root..."
  cp -r /config/output/* /usr/share/nginx/html

  echo "Done at $(date)"
  sleep 3600  # 1 hour
done &

echo "Starting nginx..."
nginx -g "daemon off;"
