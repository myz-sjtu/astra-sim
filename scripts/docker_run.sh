#!/usr/bin/sh

docker run \
    -d --name astra-sim-arn-dev \
    --shm-size=8g \
    --network host \
    -v /home/ubuntu/zmy/astra-sim:/root/astra-sim \
    astra-sim:arn-dev \
    tail -f /dev/null