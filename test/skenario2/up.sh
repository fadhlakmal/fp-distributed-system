#!/bin/bash
set -x

docker compose -f ../../group/docker-compose.yaml up -d

sleep 15

bash ../../group/join.sh