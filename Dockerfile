FROM python:3.13-alpine AS base

WORKDIR /app

RUN apk add --no-cache gcc musl-dev libffi-dev python3-dev py3-pip bash curl nginx
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
COPY start.sh /start.sh
RUN chmod +x /start.sh

FROM nginx:alpine
COPY --from=base /app /app
COPY --from=base /start.sh /start.sh

RUN apk add --no-cache python3 py3-pip bash curl && pip install --break-system-packages -r /app/requirements.txt
RUN mkdir -p /run/nginx
RUN mkdir -p /usr/share/nginx/html

WORKDIR /app
EXPOSE 80
CMD ["bash", "/start.sh"]
