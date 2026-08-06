#!/usr/bin/sh

# using proxies in the host file.

docker build \
    --build-arg HTTP_PROXY=http://localhost:21004 \
    --build-arg HTTPS_PROXY=http://localhost:21004 \
    --build-arg NO_PROXY=localhost,127.0.0.1,.local \
    --network host \
    -t astra-sim:arn-dev -f Dockerfile .
