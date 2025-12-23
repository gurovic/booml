FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /workspace

# Build toolchain is required because Python 3.14 often lacks prebuilt wheels
# for scientific packages (numpy/scipy/pandas) and they fall back to source builds.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gfortran \
        pkg-config \
        libopenblas-dev \
        liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Install a minimal toolset for notebook sessions.
COPY docker_requirements.txt /tmp/docker_requirements.txt
RUN python -m pip install --prefer-binary -r /tmp/docker_requirements.txt && \
    rm /tmp/docker_requirements.txt

# Контейнер держится живым; агент стартует через docker exec.
CMD ["sleep", "infinity"]
