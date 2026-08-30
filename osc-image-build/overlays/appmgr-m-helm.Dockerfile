FROM docker.io/r2labuser/ric-plt-appmgr:0.5.9

USER root

ARG HELM_VERSION=3.14.4
ARG HELM_SHA256=a5844ef2c38ef6ddf3b5a8f7d91e7e0e8ebc39a38bb3fc8013d629c1ef29c259

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates wget \
    && wget -q "https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz" \
    && echo "${HELM_SHA256}  helm-v${HELM_VERSION}-linux-amd64.tar.gz" | sha256sum -c - \
    && tar -xzf "helm-v${HELM_VERSION}-linux-amd64.tar.gz" \
    && install -m 0755 linux-amd64/helm /usr/local/bin/helm \
    && rm -rf linux-amd64 "helm-v${HELM_VERSION}-linux-amd64.tar.gz" \
    && apt-get purge -y wget \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*
