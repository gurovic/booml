FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_PROGRESS=1 \
    PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

WORKDIR /app

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        gfortran \
        pkg-config \
        libopenblas-dev \
        liblapack-dev \
        curl; \
    if ! command -v docker >/dev/null 2>&1; then \
        apt-get install -y --no-install-recommends docker-cli || \
        apt-get install -y --no-install-recommends moby-cli || \
        apt-get install -y --no-install-recommends docker.io || true; \
    fi; \
    if [ ! -x /usr/bin/docker ] && [ -x /usr/bin/docker.io ]; then ln -s /usr/bin/docker.io /usr/bin/docker; fi; \
    curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR="/usr/local/bin" sh; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN uv pip install --system -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Application source is bind-mounted by docker compose, so we do not copy it here.

EXPOSE 8100

CMD ["python", "manage.py", "runserver", "0.0.0.0:8100"]
