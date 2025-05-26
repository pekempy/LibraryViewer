FROM python:3.13-alpine AS builder
WORKDIR /app

RUN apk add --no-cache gcc musl-dev libffi-dev python3-dev py3-pip bash curl nginx

COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN python fetch_and_build.py

RUN mkdir -p /run/nginx

# Add cron-like loop script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Final stage
FROM nginx:alpine
COPY --from=builder /app/output /usr/share/nginx/html
COPY --from=builder /start.sh /start.sh
COPY --from=builder /app /app
RUN apk add --no-cache python3 py3-pip bash curl && pip install -r /app/requirements.txt

WORKDIR /app
EXPOSE 80
CMD ["bash", "/start.sh"]
