# run second, when all nodes are up for the first time

docker exec -it node1 mysql -uroot -ppass -e "
    SET GLOBAL group_replication_bootstrap_group=ON; 
    START GROUP_REPLICATION; 
    SET GLOBAL group_replication_bootstrap_group=OFF;
"

docker exec node2 mysql -uroot -ppass -e "
    STOP GROUP_REPLICATION;
    RESET MASTER;
    START GROUP_REPLICATION;"

docker exec node3 mysql -uroot -ppass -e "
    STOP GROUP_REPLICATION;
    RESET MASTER;
    START GROUP_REPLICATION;"

sed -i 's/loose-group_replication_start_on_boot = OFF/loose-group_replication_start_on_boot = ON/g' config/*.cnf

sleep 2
docker exec -it node1 mysql -uroot -ppass -e "SELECT * FROM performance_schema.replication_group_members;"