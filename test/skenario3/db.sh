#!/bin/bash

docker exec node1 mysql -uroot -ppass -e "
    CREATE DATABASE IF NOT EXISTS partition_test;
    USE partition_test;
    
    DROP TABLE IF EXISTS network_partition_test;
    CREATE TABLE network_partition_test (
        id INT AUTO_INCREMENT PRIMARY KEY,
        data VARCHAR(500),
        node_source VARCHAR(50),
        created_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3)
    );
"

for i in {1..100}; do
    docker exec node1 mysql -uroot -ppass partition_test -e "
        INSERT INTO network_partition_test (data, node_source) VALUES
        ('Baseline data', 'node1');
    "
done

sleep 2

echo "Checking database records..."
echo ""
for NODE in node1 node2 node3; do
    COUNT=$(docker exec $NODE mysql -uroot -ppass partition_test \
            -sN -e "SELECT COUNT(*) FROM network_partition_test;" 2>/dev/null)
    echo "  $NODE: $COUNT records"
done