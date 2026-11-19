# ---- Stage 1: build the front end ----
FROM node:24-slim AS web
WORKDIR /web
COPY auditagent-web/package.json auditagent-web/package-lock.json ./
RUN npm ci
COPY auditagent-web/ ./
# The same address as .env.production: the API lives under /api when one server serves both.
ENV VITE_API_BASE_URL=/api
RUN npm run build

# ---- Stage 2: the server (API + the built front end) ----
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    HF_HOME=/opt/hf \
    AUDITAGENT_WEB_DIR=/app/web \
    AUDITAGENT_JOBS_DIR=/data/jobs \
    AUDITAGENT_DB=/data/auditagent.db
WORKDIR /app

# torch from the CPU index: the default wheel brings a few GB of GPU libraries that a t3 server cannot use.
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir fastapi python-multipart

# The embedding model is baked into the image, so the first audit does not wait for a download.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY src ./src
COPY --from=web /web/dist ./web

RUN useradd --create-home app \
 && mkdir -p /data/jobs \
 && chown -R app /data /opt/hf
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/health')" || exit 1

CMD ["uvicorn", "auditagent.api.web:create_web_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
