FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install only runtime packages required by pyproj.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libproj-dev \
       proj-data \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY templates ./templates

# Run as an unprivileged user to reduce container breakout risk.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/healthz', timeout=3)"

CMD ["gunicorn", "-w", "2", "-k", "gthread", "--threads", "4", "--timeout", "60", "-b", "0.0.0.0:5000", "main:app"]
