#!/bin/bash
while true; do
    clear
    echo "=== CLUSTER STATUS ==="
    for NODE in node1 node2 node3; do
        COUNT=$(docker exec $NODE mysql -uroot -ppass failover_test \
                -sN -e "SELECT COUNT(*) FROM transactions;" 2>/dev/null)
        STATUS=$(docker exec $NODE mysql -uroot -ppass \
                -sN -e "SELECT MEMBER_STATE FROM performance_schema.replication_group_members 
                WHERE MEMBER_HOST='$NODE';" 2>/dev/null)
        ROLE=$(docker exec $NODE mysql -uroot -ppass \
                -sN -e "SELECT MEMBER_ROLE FROM performance_schema.replication_group_members 
                WHERE MEMBER_HOST='$NODE';" 2>/dev/null)
        echo "$NODE: $COUNT records | State: $STATUS | Role: $ROLE"
    done
    sleep 2
done