#!/bin/bash
set -x

docker compose -f ../../group/docker-compose.yaml down -v

sleep 15

sudo rm -rf ../../group/mysql1_data ../../group/mysql2_data ../../group/mysql3_data