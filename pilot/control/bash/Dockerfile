# Copied unchanged from ControlArena 19.0.0 (control_arena/settings/bash/Dockerfile, MIT licence,
# Copyright (c) 2025 UK AI Security Institute), so that the build context is inside this repository.
# One path of the installed package still goes into the log: ControlArena loads `bash_tasks.json` by
# its absolute path and Inspect records that as the dataset location. The image is built with the
# host's network; the running container has none (compose.yaml next to this file). `alpine:latest` is
# not pinned upstream: the manifest records the image the run used.
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
