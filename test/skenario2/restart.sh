#!/bin/bash
set -x

docker compose -f ../../group/docker-compose.yaml up -d node1

sleep 15

docker exec -it node1 mysql -uroot -ppass -e "
    CHANGE MASTER TO MASTER_USER='repl', MASTER_PASSWORD='repl' FOR CHANNEL 'group_replication_recovery';
    START GROUP_REPLICATION;
    SELECT * FROM performance_schema.replication_group_members;
"