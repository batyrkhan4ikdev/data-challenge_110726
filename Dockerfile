FROM node:24-slim AS web
WORKDIR /src
COPY web/package.json web/package-lock.json* web/
RUN if [ -f web/package-lock.json ]; then npm ci --prefix web; else npm install --prefix web; fi
COPY web/ web/
RUN npm run build --prefix web

FROM python:3.14-slim
# ffmpeg converts uploaded wav/ogg/m4a/webm/flac to MP3 for the ASR client
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 cqa
WORKDIR /app
COPY pyproject.toml ./
COPY server/ server/
RUN pip install --no-cache-dir .
COPY config/ config/
COPY data/ data/
COPY web/ web/
COPY --from=web /src/web/dist web/dist
RUN mkdir -p data/store data/cache && chown -R cqa:cqa data
USER cqa
EXPOSE 8787
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8787"]
