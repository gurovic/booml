FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install base Python packages
COPY docker_requirements.txt /tmp/docker_requirements.txt
RUN pip install --no-cache-dir -r /tmp/docker_requirements.txt && \
    rm /tmp/docker_requirements.txt

WORKDIR /workspace

# Контейнер держится живым; агент стартует через docker exec.
CMD ["sleep", "infinity"]
