#!/bin/bash

echo "Current cluster state:"
docker exec node1 mysql -uroot -ppass -e "
    SELECT *
    FROM performance_schema.replication_group_members
    ORDER BY MEMBER_ROLE DESC;
" 2>/dev/null

echo ""
echo "Isolating node1 from cluster network..."
docker network disconnect group_mysql-cluster node1
sleep 10

echo ""
echo "Checking updated cluster status on node2 (majority partition):"
docker exec node2 mysql -uroot -ppass -e "
    SELECT *
    FROM performance_schema.replication_group_members
    ORDER BY MEMBER_ROLE DESC;
" 2>/dev/null

