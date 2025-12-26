FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gfortran \
        pkg-config \
        libopenblas-dev \
        liblapack-dev \
        curl \
        docker.io \
    && if [ ! -x /usr/bin/docker ]; then apt-get install -y --no-install-recommends docker-cli || apt-get install -y --no-install-recommends moby-cli; fi \
    && if [ ! -x /usr/bin/docker ] && [ -x /usr/bin/docker.io ]; then ln -s /usr/bin/docker.io /usr/bin/docker; fi \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Application source is bind-mounted by docker compose, so we do not copy it here.

EXPOSE 8100

CMD ["python", "manage.py", "runserver", "0.0.0.0:8100"]
