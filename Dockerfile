# Web app build
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# API + data
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY fetch_data.sh ./
RUN mkdir -p data && ./fetch_data.sh && rm -rf data/hadith-api data/quran-api
COPY --from=web /web/dist frontend/dist

WORKDIR /app/backend
ENV PORT=8000
CMD uvicorn api:app --host 0.0.0.0 --port ${PORT}
