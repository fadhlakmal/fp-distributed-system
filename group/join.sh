docker exec -it node1 mysql -uroot -ppass -e "
    SET GLOBAL group_replication_bootstrap_group=ON; 
    START GROUP_REPLICATION; 
    SET GLOBAL group_replication_bootstrap_group=OFF;
"

# docker exec -it node1 mysql -uroot -ppass -e "
#     CREATE USER IF NOT EXISTS 'repl'@'%' IDENTIFIED BY 'password';
#     GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
#     FLUSH PRIVILEGES;
# "

docker exec -it node2 mysql -uroot -ppass -e "
    RESET MASTER;
    CHANGE MASTER TO 
        MASTER_USER='root',
        MASTER_PASSWORD='pass'
    FOR CHANNEL 'group_replication_recovery';
    START GROUP_REPLICATION;
"

docker exec -it node3 mysql -uroot -ppass -e "
    RESET MASTER;
    CHANGE MASTER TO 
        MASTER_USER='root',
        MASTER_PASSWORD='pass'
    FOR CHANNEL 'group_replication_recovery';
    START GROUP_REPLICATION;
"

docker exec -it node1 mysql -uroot -ppass -e "SELECT * FROM performance_schema.replication_group_members;"