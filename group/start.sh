# run first

sed -i 's/loose-group_replication_start_on_boot = ON/loose-group_replication_start_on_boot = OFF/g' config/*.cnf
docker compose up -d