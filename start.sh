#!/bin/bash

echo "Ensuring /config/output exists and has loading screen..."
mkdir -p /config/output
cp /app/templates/loading.html /config/output/index.html

echo "Linking Nginx root to /config/output..."
rm -rf /usr/share/nginx/html
ln -s /config/output /usr/share/nginx/html

echo "Starting fetch_and_build loop..."

while true; do
  echo "Running fetch_and_build.py at $(date)"
  python3 /app/fetch_and_build.py
  echo "Done at $(date)"
  sleep 3600
done &

echo "Starting nginx..."
nginx -g "daemon off;"
