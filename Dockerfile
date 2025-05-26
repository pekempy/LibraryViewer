# ---- Stage 1: Build the static site ----
FROM python:3.11-alpine AS builder
WORKDIR /app

# Install system dependencies needed for pip
RUN apk add --no-cache gcc musl-dev libffi-dev python3-dev py3-pip

COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN python fetch_and_build.py

# ---- Stage 2: Serve using nginx ----
FROM nginx:alpine
COPY --from=builder /app/output /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
