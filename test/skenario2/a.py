loose-group_replication_bootstrap_group = OFF
loose-group_replication_start_on_boot = OFF
loose-group_replication_ssl_mode = REQUIRED
loose-group_replication_recovery_use_ssl = 1

loose-group_replication_group_name = "aaaaaaaa-bbbb-cccc-dddd-eeeeffff0000"
loose-group_replication_ip_allowlist = "node1,node2,node3"
loose-group_replication_group_seeds = "node1:33061,node2:33061,node3:33061"


[Warning] Members removed from the group: node1:3306
[System] Primary server with address node1:3306 left the group. Electing new Primary.