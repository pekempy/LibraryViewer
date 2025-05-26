#!/bin/bash

echo "⚡ Starting background fetcher loop..."
# Loop every 3 hours in background
while true; do
  python3 fetch_and_build.py && echo "✅ Updated at $(date)"
  sleep 10800  # 3 hours
done &

echo "🚀 Starting nginx..."
nginx -g "daemon off;"
