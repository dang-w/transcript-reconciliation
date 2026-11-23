# The body below is ControlArena's control_arena/settings/bash/Dockerfile (the same file in 19.0.0 and
# 20.1.1; MIT licence, Copyright (c) 2025 UK AI Security Institute) with one line changed: the base image.
# It is copied so that the build context is inside this repository. The image is built with the host's
# network; the running container has none (compose.yaml next to this file).
#
# Upstream has `FROM alpine:latest`. From run B the base image is pinned to the digest that `alpine:latest`
# had for the pilot and run A (Alpine 3.24.4). The `apk` and `pip` lines below are not pinned: the manifest
# records the image a run used.
FROM alpine@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf

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
