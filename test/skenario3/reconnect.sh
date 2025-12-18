#!/bin/bash

echo "Reconnecting node1 to cluster network..."
docker network connect group_mysql-cluster node1

sleep 10

STATE=$(docker exec node1 mysql -uroot -ppass \
    -sN -e "SELECT MEMBER_STATE FROM performance_schema.replication_group_members 
    WHERE MEMBER_HOST='node1';" 2>/dev/null || echo "ERROR")

echo ""
if [ "$STATE" = "ONLINE" ]; then
    echo "node1 automatically rejoined and is ONLINE"
else
    echo "node1 not online yet (State: $STATE)"
    echo "Attempting to manually restart Group Replication..."

    docker exec node1 mysql -uroot -ppass -e "
        STOP GROUP_REPLICATION;
        START GROUP_REPLICATION;
    " 2>/dev/null
    
    echo ""
    echo "Waiting for node1 to rejoin..."
    sleep 10
    
    STATE=$(docker exec node1 mysql -uroot -ppass \
        -sN -e "SELECT MEMBER_STATE FROM performance_schema.replication_group_members 
        WHERE MEMBER_HOST='node1';" 2>/dev/null || echo "ERROR")
    
    echo ""
    if [ "$STATE" = "ONLINE" ]; then
        echo "node1 successfully rejoined and is ONLINE"
    else
        echo "node1 still not online (State: $STATE)"
    fi
fi

docker exec node1 mysql -uroot -ppass -e "
    SELECT 
        MEMBER_HOST,
        MEMBER_STATE,
        MEMBER_ROLE
    FROM performance_schema.replication_group_members
    ORDER BY MEMBER_ROLE DESC;
"

echo ""
echo "Waiting for data synchronization..."
sleep 3

echo ""
echo "Final record counts:"
for NODE in node1 node2 node3; do
    COUNT=$(docker exec $NODE mysql -uroot -ppass partition_test \
            -sN -e "SELECT COUNT(*) FROM network_partition_test;" 2>/dev/null || echo "ERROR")
    echo "  $NODE: $COUNT records"
done

echo ""
echo "Checking data written during partition:"
docker exec node1 mysql -uroot -ppass partition_test -e "
    SELECT 
        id,
        data,
        node_source,
        created_at
    FROM network_partition_test
    WHERE data = 'Write during partition'
    ORDER BY id;
"