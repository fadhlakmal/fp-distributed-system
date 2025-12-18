#!/bin/bash

echo "Starting continuous cluster monitoring..."
echo "Press Ctrl+C to stop"
echo ""
sleep 2

while true; do
    clear
    date
    echo ""
    
    echo "--- Container Status ---"
    for NODE in node1 node2 node3; do
        STATUS=$(docker inspect -f '{{.State.Running}}' $NODE 2>/dev/null || echo "not found")
        if [ "$STATUS" = "true" ]; then
            echo "  $NODE: RUNNING"
        else
            echo "  $NODE: STOPPED/ERROR"
        fi
    done
    echo ""
    
    echo "--- Network Connectivity ---"
    for NODE in node1 node2 node3; do
        NETWORKS=$(docker inspect -f '{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}' $NODE 2>/dev/null || echo "error")
        if [[ "$NETWORKS" == *"mysql-cluster"* ]]; then
            echo "  $NODE: Connected to cluster network"
        else
            echo "  $NODE: ISOLATED from cluster network"
        fi
    done
    echo ""
    
    echo "--- Group Replication Status ---"
    for NODE in node1 node2 node3; do
        RESULT=$(docker exec $NODE mysql -uroot -ppass \
                -sN -e "SELECT CONCAT(MEMBER_STATE, '|', MEMBER_ROLE) 
                FROM performance_schema.replication_group_members 
                WHERE MEMBER_HOST='$NODE';" 2>/dev/null || echo "ERROR|UNKNOWN")
        
        STATE=$(echo $RESULT | cut -d'|' -f1)
        ROLE=$(echo $RESULT | cut -d'|' -f2)
        
        COUNT=$(docker exec $NODE mysql -uroot -ppass partition_test \
                -sN -e "SELECT COUNT(*) FROM network_partition_test;" 2>/dev/null || echo "N/A")
        
        printf "  %-10s State: %-12s Role: %-10s Records: %s\n" \
               "$NODE" "$STATE" "$ROLE" "$COUNT"
    done
    
    echo ""
    echo "--- Quorum Status ---"
    
    for node in node1 node2 node3; do
        cluster_data=$(docker exec $node mysql -uroot -ppass -t -e \
        "SELECT MEMBER_HOST, MEMBER_STATE, MEMBER_ROLE 
         FROM performance_schema.replication_group_members;" 2>/dev/null)
    
        echo "$cluster_data"
        echo ""
        
        if [ -z "$cluster_data" ]; then
            echo " No nodes accessible from $node"
            return 1
        fi
        
        online_count=$(echo "$cluster_data" | grep -c "ONLINE")
        total_count=$(echo "$cluster_data" | grep -c "|.*node")
        quorum_needed=$(( (total_count / 2) + 1 ))
        
        echo "   Cluster health: $online_count out of $total_count nodes online"
        echo "   (quorum requires $quorum_needed nodes)"
        echo ""
        
        if [ $online_count -ge $quorum_needed ]; then
            echo "Quorum achieved - cluster accepting writes"
        else
            echo "Lost quorum - cluster is read-only"
        fi
    done
    
    sleep 3
done

