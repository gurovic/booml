FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_PROGRESS=1

WORKDIR /workspace

# Build toolchain is required because Python 3.14 often lacks prebuilt wheels
# for scientific packages (numpy/scipy/pandas) and they fall back to source builds.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gfortran \
        pkg-config \
        libopenblas-dev \
        liblapack-dev \
        curl \
    && curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR="/usr/local/bin" sh \
    && rm -rf /var/lib/apt/lists/*

# Install a minimal toolset for notebook sessions.
COPY docker_requirements.txt /tmp/docker_requirements.txt
RUN uv pip install --system -r /tmp/docker_requirements.txt && \
    rm /tmp/docker_requirements.txt

# Контейнер держится живым; агент стартует через docker exec.
CMD ["sleep", "infinity"]
