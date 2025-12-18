#!/bin/bash

TIMESTAMP=$(date +%s)

echo "[TEST 1] Attempting INSERT on ISOLATED node1 (should FAIL)..."
RESULT=$(timeout 5 docker exec node1 mysql -uroot -ppass partition_test \
    -e "INSERT INTO network_partition_test (data, node_source) VALUES ('Write during partition', 'node1-isolated');" \
    2>&1)
EXIT_CODE=$?

if [[ $EXIT_CODE -eq 124 ]]; then
    echo "Result: Transaction blocked"
    echo "node1 lost quorum and cannot commit writes."
else
    echo "Write succeeded"
    echo "Isolated node should NOT accept writes!"
fi

echo ""
echo "Finding PRIMARY and SECONDARY node in majority partition..."

PRIMARY_NODE=""
SECONDARY_NODE=""

for NODE_NAME in node2 node3; do
    ROLE=$(docker exec $NODE_NAME mysql -uroot -ppass -sN -e "
        SELECT MEMBER_ROLE FROM performance_schema.replication_group_members 
        WHERE MEMBER_STATE='ONLINE' AND MEMBER_HOST='$NODE_NAME';" 2>/dev/null)
    
    case "$ROLE" in
        "PRIMARY")
            PRIMARY_NODE=$NODE_NAME
            ;;
        "SECONDARY")
            SECONDARY_NODE=$NODE_NAME
            ;;
    esac
done

if [[ -z "$PRIMARY_NODE" ]]; then
    echo "ERROR: No PRIMARY found in majority partition!"
    exit 1
fi

echo ""
echo "Current PRIMARY: $PRIMARY_NODE"
echo "Current SECONDARY: $SECONDARY_NODE"
echo ""
echo "[TEST 2] Attempting INSERT on PRIMARY node (should SUCCEED)..."

RESULT2=$(docker exec $PRIMARY_NODE mysql -uroot -ppass partition_test \
    -e "INSERT INTO network_partition_test (data, node_source) VALUES ('Write during partition', '$PRIMARY_NODE-quorum');" \
    2>&1)

echo ""
if [[ $RESULT2 != *"ERROR"* ]]; then
    echo "SUCCESS (Expected behavior)"
    echo "Write committed successfully on $PRIMARY_NODE"
else
    echo "FAILED (unexpected!)"
    echo "Error: $RESULT2"
fi

echo ""
echo "[TEST 3] Attempting INSERT on SECONDARY node (should FAIL)..."
RESULT3=$(docker exec $SECONDARY_NODE mysql -uroot -ppass partition_test \
    -e "INSERT INTO network_partition_test (data, node_source) VALUES ('Write during partition', 'node3-quorum');" \
    2>&1)

echo ""
if [[ $RESULT3 == *"super-read-only"* ]] || [[ $RESULT3 == *"read-only"* ]]; then
    echo "SUCCESS (Expected behavior)"
    echo "Secondary correctly rejected write - it's in read-only mode"
else
    echo "UNEXPECTED: Secondary accepted write (should not happen!)"
    echo "Error: $RESULT3"
fi

echo ""
echo "Isolated partition (node1):"
COUNT1=$(docker exec node1 mysql -uroot -ppass partition_test \
    -sN -e "SELECT COUNT(*) FROM network_partition_test;" 2>/dev/null || echo "ERROR")
echo "node1: $COUNT1 records"

echo ""
echo "Majority partition (node2, node3):"
COUNT2=$(docker exec node2 mysql -uroot -ppass partition_test \
    -sN -e "SELECT COUNT(*) FROM network_partition_test;" 2>/dev/null || echo "ERROR")
COUNT3=$(docker exec node3 mysql -uroot -ppass partition_test \
    -sN -e "SELECT COUNT(*) FROM network_partition_test;" 2>/dev/null || echo "ERROR")
echo "node2: $COUNT2 records"
echo "node3: $COUNT3 records"

echo ""
echo "Observation:"
if [ "$COUNT2" = "$COUNT3" ] && [ "$COUNT2" -gt "$COUNT1" ]; then
    echo "Majority partition (node2, node3) has MORE records than isolated node1"
    echo "Node2 and node3 are synchronized"
else
    echo "Unexpected count distribution"
fi