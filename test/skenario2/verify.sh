#!/bin/bash
set -x

docker exec -it node2 mysql -uroot -ppass -e "
    USE failover_test;
    SELECT COUNT(*) AS total_records, MIN(id) AS first_id,
       MAX(id) AS last_id, MIN(created_at) AS earliest,
       MAX(created_at) AS latest
    FROM transactions;
"

docker exec -it node2 mysql -uroot -ppass -e "
    USE failover_test;
    SELECT (t1.id + 1) AS missing_id_start,
        (MIN(t2.id) - 1) AS missing_id_end,
        (MIN(t2.id) - t1.id - 1) AS gap_size
    FROM transactions t1
    LEFT JOIN transactions t2 ON t2.id > t1.id
    GROUP BY t1.id
    HAVING gap_size > 0;
"