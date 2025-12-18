#!/bin/bash
set -x

docker exec -it node1 mysql -uroot -ppass -e "
    CREATE DATABASE IF NOT EXISTS failover_test;
    SHOW DATABASES;
    USE failover_test;

    CREATE TABLE IF NOT EXISTS transactions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        data VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        node_name VARCHAR(50) NOT NULL,
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB;

    SHOW TABLES;
"