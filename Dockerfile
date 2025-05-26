FROM python:3.13-alpine AS base
WORKDIR /app

RUN apk add --no-cache gcc musl-dev libffi-dev python3-dev py3-pip bash curl nginx

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# Copy static nginx config (or leave default)
RUN mkdir -p /run/nginx

# Start both fetcher loop and nginx in foreground
CMD ["bash", "-c", "\
    python3 fetch_and_build.py && \
    cp -r output/* /usr/share/nginx/html && \
    (while true; do sleep 10800; echo '⏰ Updating site...'; python3 fetch_and_build.py && cp -r output/* /usr/share/nginx/html; done) & \
    nginx -g 'daemon off;' \
"]
