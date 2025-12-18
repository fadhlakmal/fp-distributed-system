-- ! A. Performance Schema Tables
-- Status anggota group
SELECT * FROM performance_schema.replication_group_members;

-- Statistik replikasi per member
SELECT * FROM performance_schema.replication_group_member_stats;

-- ! B. System Variables dan Status
-- Identifikasi primary member saat ini
SHOW VARIABLES LIKE 'group_replication_primary_member';

-- Status operasional group replication
SHOW STATUS LIKE 'group_replication%';

docker exec -it node2 mysql -uroot -ppass -e "
    SELECT * FROM performance_schema.replication_group_members;
"

docker exec node2 mysql -uroot -ppass -e "
    SET GLOBAL general_log = 'ON';
    SET GLOBAL log_output = 'TABLE';
"

SELECT * FROM performance_schema.replication_group_members;


