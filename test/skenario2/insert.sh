#!/bin/bash
TARGET_NODE="node1"
DATABASE="failover_test"
INTERVAL=0.5

COUNTER=1
echo "Starting continuous workload at $(date)"

while true; do
    if docker exec $TARGET_NODE mysql -uroot -ppass $DATABASE -e \
        "INSERT INTO transactions (data, node_name) 
         VALUES ('Data-$COUNTER', @@hostname);" 2>/dev/null; then
        echo "[$(date +%H:%M:%S)] ✓ Inserted record $COUNTER"
    else
        echo "[$(date +%H:%M:%S)] ✗ Failed to insert record $COUNTER"
    fi
    COUNTER=$((COUNTER + 1))
    sleep $INTERVAL
done