docker exec -it primary mysql -uroot -ppass -e "
    CREATE USER 'repl'@'%' IDENTIFIED BY 'password';
    GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
    FLUSH PRIVILEGES;
"

docker exec -it replica1 mysql -uroot -ppass -e "
    RESET MASTER;
    CHANGE MASTER TO 
        MASTER_HOST='primary',
        MASTER_USER='repl',
        MASTER_PASSWORD='password',
        MASTER_AUTO_POSITION=1,
        GET_MASTER_PUBLIC_KEY=1;
    START SLAVE;
"

docker exec -it replica2 mysql -uroot -ppass -e "
    RESET MASTER;
    CHANGE MASTER TO 
        MASTER_HOST='primary',
        MASTER_USER='repl',
        MASTER_PASSWORD='password',
        MASTER_AUTO_POSITION=1,
        GET_MASTER_PUBLIC_KEY=1;
    START SLAVE;
"

docker exec -it replica1 mysql -uroot -ppass -e "SHOW SLAVE STATUS\G"
docker exec -it replica2 mysql -uroot -ppass -e "SHOW SLAVE STATUS\G"