#!/bin/bash

cd ../../group

docker compose down

sudo rm -rf mysql1_data mysql2_data mysql3_data

docker network rm mysql-cluster 2>/dev/null || echo "  Network already removed or doesn't exist"

sed -i 's/loose-group_replication_start_on_boot = ON/loose-group_replication_start_on_boot = OFF/g' config/*.cnf

