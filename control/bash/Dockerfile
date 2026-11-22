# The body below is ControlArena's control_arena/settings/bash/Dockerfile, unchanged: the file is the same
# in 19.0.0 and 20.1.1 (MIT licence,
# Copyright (c) 2025 UK AI Security Institute). It is copied so that the build context is inside this
# repository. The image is built with the host's network; the running container has none (compose.yaml
# next to this file). `alpine:latest` is not pinned upstream: the manifest records the image a run used.
FROM alpine:latest

RUN apk add --no-cache python3 py3-pip bash curl sudo py3-psutil

# Create venv and install without playwright, inheriting system packages
RUN python3 -m venv --system-site-packages /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install inspect-tool-support without dependencies, then add needed ones as we can't use playwright in Alpine
RUN pip install --no-deps inspect-tool-support && \
    pip install aiohttp httpx jsonrpcserver mcp packaging pydantic returns semver tenacity

# Try running post-install
RUN inspect-tool-support post-install --no-web-browser || true

# Install pytest
RUN pip install pytest

CMD ["/bin/bash"]
