#!/bin/bash

set -e

cd ../../group

echo "Starting cluster..."
bash start.sh

echo ""
echo "Waiting for containers to initialize..."
sleep 75

echo ""
echo "Initializing Group Replication..."
bash join.sh
