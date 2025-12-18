#!/bin/bash

for NODE in node1 node2 node3; do
    COUNT=$(docker exec $NODE mysql -uroot -ppass failover_test \
            -sN -e "SELECT COUNT(*) FROM transactions;")
    echo "$NODE: $COUNT records"
done

set -x
docker stop node1
docker rm node1