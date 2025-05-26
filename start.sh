#!/bin/bash

echo "Starting fetch_and_build loop..."

# Background loop: re-fetch every 3 hours
while true; do
  echo "Running fetch_and_build.py at $(date)"
  python3 /app/fetch_and_build.py

  echo "Copying output to nginx root..."
  cp -r /config/output/* /usr/share/nginx/html

  echo "Done at $(date)"
  sleep 10800  # 3 hours
done &

echo "Starting nginx..."
nginx -g "daemon off;"
