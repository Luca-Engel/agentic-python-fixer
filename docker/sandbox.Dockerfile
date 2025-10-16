FROM python:3.12.11-slim

# System deps (optional but handy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Python deps for test running
RUN pip install --no-cache-dir pytest==8.3.2 pytest-timeout==2.3.1

# Create non-root user (avoid root inside container)
RUN useradd -ms /bin/bash runner
USER runner

WORKDIR /workspace
ENV PYTHONHASHSEED=0