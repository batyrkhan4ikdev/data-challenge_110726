FROM node:24-slim AS web
WORKDIR /src
COPY web/package.json web/package-lock.json* web/
RUN if [ -f web/package-lock.json ]; then npm ci --prefix web; else npm install --prefix web; fi
COPY web/ web/
RUN npm run build --prefix web

FROM python:3.14-slim
WORKDIR /app
COPY pyproject.toml ./
COPY server/ server/
RUN pip install --no-cache-dir .
COPY config/ config/
COPY data/ data/
COPY web/ web/
COPY --from=web /src/web/dist web/dist
EXPOSE 8787
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8787"]
