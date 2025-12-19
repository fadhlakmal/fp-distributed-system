import mysql.connector
from mysql.connector import Error
import docker
import time
import threading
from datetime import datetime
from collections import defaultdict
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Tuple
import subprocess
import sys

# Constants
WORKLOAD_INTERVAL = 0.5  # seconds between inserts
INITIAL_WORKLOAD_DURATION = 10  # seconds
POST_FAILOVER_WORKLOAD_DURATION = 10  # seconds
MYSQL_STARTUP_WAIT = 10  # seconds
CLUSTER_REJOIN_WAIT = 15  # seconds
CONSISTENCY_CHECK_WAIT = 5  # seconds
FAILOVER_MAX_WAIT = 60  # seconds
FAILOVER_CHECK_INTERVAL = 2  # seconds
PRIMARY_RETRY_ATTEMPTS = 3
PRIMARY_RETRY_DELAY = 0.2  # seconds

class GroupReplicationFailoverTest:
    def __init__(self, compose_file_path: str = "/home/reynaldineo/sister/fp/group/docker-compose.yaml"):
        """Initialize the failover test with configuration."""
        self.client = docker.from_env()
        self.compose_file_path = compose_file_path
        
        self.nodes: Dict[str, Dict[str, Any]] = {
            'node1': {'host': 'localhost', 'port': 3306, 'container': 'node1'},
            'node2': {'host': 'localhost', 'port': 3307, 'container': 'node2'},
            'node3': {'host': 'localhost', 'port': 3308, 'container': 'node3'}
        }
        
        self.db_config = {
            'user': 'root',
            'password': 'pass',
            'database': 'failover_test'
        }
        
        # Tracking variables
        self.workload_running = False
        self.workload_stats = {
            'total_attempts': 0,
            'successful_inserts': 0,
            'failed_inserts': 0,
            'errors': defaultdict(int)
        }
        self.failover_detected = False
        self.failover_start_time: Optional[float] = None
        self.failover_end_time: Optional[float] = None

    @contextmanager
    def get_connection(self, node_name: str, silent: bool = False):
        connection = None
        try:
            node = self.nodes[node_name]
            connection = mysql.connector.connect(
                host=node['host'],
                port=node['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                autocommit=False
            )
            yield connection
        except Error as e:
            if not silent:
                print(f"❌ Error connecting to {node_name}: {e}")
            yield None
        finally:
            if connection and connection.is_connected():
                connection.close()

    def execute_query(self, connection, query: str, fetch: bool = False) -> Optional[Any]:
        if not connection:
            return None
            
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query)
                if fetch:
                    return cursor.fetchall()
                connection.commit()
                return True
        except Error as e:
            print(f"❌ Query error: {e}")
            return None

    def check_group_replication_status(self, node_name: str) -> Optional[List[Dict[str, Any]]]:
        query = """
        SELECT 
            MEMBER_ID,
            MEMBER_HOST,
            MEMBER_PORT,
            MEMBER_STATE,
            MEMBER_ROLE,
            MEMBER_VERSION
        FROM performance_schema.replication_group_members
        ORDER BY MEMBER_ROLE DESC, MEMBER_PORT
        """
        
        with self.get_connection(node_name, silent=True) as conn:
            if conn:
                return self.execute_query(conn, query, fetch=True)
        return None

    def get_primary_node(self) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        for node_name in self.nodes.keys():
            status = self.check_group_replication_status(node_name)
            
            if status:
                primary_member = self._find_primary_in_status(status)
                if primary_member:
                    node_name = self._map_host_to_node(primary_member['MEMBER_HOST'])
                    if node_name:
                        return node_name, primary_member
                # No primary found in this status, might be mid-election
                return None, None
                
        return None, None
    
    def _find_primary_in_status(self, status: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find PRIMARY member in status list."""
        for member in status:
            if member['MEMBER_ROLE'] == 'PRIMARY':
                return member
        return None
    
    def _map_host_to_node(self, host: str) -> Optional[str]:
        """Map member host to local node configuration."""
        for name, config in self.nodes.items():
            if config['container'] == host:
                return name
        print(f"⚠️ Found PRIMARY at host '{host}' but couldn't map to local config.")
        return None

    def display_group_status(self, title: str = "Group Replication Status") -> None:
        print(f"\n{'='*80}")
        print(f"📊 {title}")
        print(f"{'='*80}")
        print(f"{'Node':<10} {'Host':<15} {'Port':<6} {'State':<12} {'Role':<10}")
        print(f"{'-'*80}")
        
        status = self._get_any_node_status()
            
        if status:
            self._print_status_rows(status)
        else:
            print("❌ Unable to retrieve group status")
        print(f"{'='*80}\n")
    
    def _get_any_node_status(self) -> Optional[List[Dict[str, Any]]]:
        """Try to get status from any available node."""
        for node_name in self.nodes.keys():
            status = self.check_group_replication_status(node_name)
            if status:
                return status
        return None
    
    def _print_status_rows(self, status: List[Dict[str, Any]]) -> None:
        """Print status rows for each member."""
        for member in status:
            node_name = self._find_node_by_port(member['MEMBER_PORT'])
            print(f"{node_name:<10} {member['MEMBER_HOST']:<15} "
                  f"{member['MEMBER_PORT']:<6} {member['MEMBER_STATE']:<12} "
                  f"{member['MEMBER_ROLE']:<10}")
    
    def _find_node_by_port(self, port: int) -> str:
        """Find node name by port number."""
        for name, config in self.nodes.items():
            if config['port'] == port:
                return name
        return ""

    def continuous_workload(self) -> None:
        """Run continuous insert workload to test failover behavior."""
        print("\n🔄 Starting continuous workload...")
        
        while self.workload_running:
            self.workload_stats['total_attempts'] += 1
            
            primary_node = self._get_primary_with_retry()
            
            if not primary_node:
                self._handle_no_primary()
                time.sleep(WORKLOAD_INTERVAL)
                continue
            
            self._check_failover_recovery()
            self._perform_insert(primary_node)
            time.sleep(WORKLOAD_INTERVAL)
    
    def _get_primary_with_retry(self) -> Optional[str]:
        """Try to get primary node with retries."""
        for retry in range(PRIMARY_RETRY_ATTEMPTS):
            primary_node, _ = self.get_primary_node()
            if primary_node:
                return primary_node
            if retry < PRIMARY_RETRY_ATTEMPTS - 1:
                time.sleep(PRIMARY_RETRY_DELAY)
        return None
    
    def _handle_no_primary(self) -> None:
        """Handle scenario when no primary is available."""
        self.workload_stats['failed_inserts'] += 1
        self.workload_stats['errors']['no_primary'] += 1
        
        if not self.failover_detected:
            self.failover_detected = True
            self.failover_start_time = time.time()
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            print(f"\n⚠️  FAILOVER DETECTED at {timestamp}")
    
    def _check_failover_recovery(self) -> None:
        """Check if failover has completed and log recovery time."""
        if self.failover_detected and not self.failover_end_time:
            self.failover_end_time = time.time()
            duration = self.failover_end_time - self.failover_start_time
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            print(f"\n✅ FAILOVER COMPLETED at {timestamp}")
            print(f"⏱️  Failover Duration: {duration:.2f} seconds")
    
    def _perform_insert(self, primary_node: str) -> None:
        """Perform a single transaction insert."""
        with self.get_connection(primary_node, silent=True) as conn:
            if not conn:
                self._record_failed_insert('connection_failed')
                return
            
            try:
                query = self._build_insert_query()
                self.execute_query(conn, query)
                self.workload_stats['successful_inserts'] += 1
                self._log_progress()
            except Error as e:
                self._record_failed_insert(f'error_{e.errno if hasattr(e, "errno") else "unknown"}')
    
    def _build_insert_query(self) -> str:
        """Build INSERT query for transaction."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        amount = 100 + (self.workload_stats['total_attempts'] % 900)
        description = f'Transaction #{self.workload_stats["total_attempts"]}'
        return f"""
            INSERT INTO transactions (transaction_time, amount, description)
            VALUES ('{timestamp}', {amount}, '{description}')
        """
    
    def _record_failed_insert(self, error_type: str) -> None:
        """Record a failed insert attempt."""
        self.workload_stats['failed_inserts'] += 1
        self.workload_stats['errors'][error_type] += 1
    
    def _log_progress(self) -> None:
        """Log workload progress periodically."""
        if self.workload_stats['total_attempts'] % 10 == 0:
            print(f"📝 Inserted {self.workload_stats['successful_inserts']} transactions "
                  f"(Attempts: {self.workload_stats['total_attempts']}, "
                  f"Failed: {self.workload_stats['failed_inserts']})")

    def setup_test_database(self) -> bool:
        print("\n🔧 Setting up test database...")
        
        primary_node, _ = self.get_primary_node()
        if not primary_node:
            print("❌ No primary node found!")
            return False
        
        with self.get_connection(primary_node) as conn:
            if not conn:
                return False
            
            try:
                with conn.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_config['database']}")
                    cursor.execute(f"USE {self.db_config['database']}")
                    cursor.execute("DROP TABLE IF EXISTS transactions")
                    cursor.execute(self._get_table_schema())
                
                conn.commit()
                print("✅ Database and table created successfully")
                return True
                
            except Error as e:
                print(f"❌ Setup error: {e}")
                return False
    
    def _get_table_schema(self) -> str:
        """Return the CREATE TABLE SQL for transactions table."""
        return """
            CREATE TABLE transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                transaction_time DATETIME(3),
                amount DECIMAL(10,2),
                description VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_time (transaction_time)
            ) ENGINE=InnoDB
        """

    def stop_container(self, container_name):
        """Stop a Docker container"""
        try:
            container = self.client.containers.get(container_name)
            print(f"\n🛑 Stopping container: {container_name}")
            container.stop()
            print(f"✅ Container {container_name} stopped")
            return True
        except Exception as e:
            print(f"❌ Error stopping container: {e}")
            return False

    def start_container(self, container_name):
        """Start a Docker container"""
        try:
            # Remove the stopped container first to avoid bind mount issues
            try:
                container = self.client.containers.get(container_name)
                print(f"\n🗑️  Removing stopped container: {container_name}")
                container.remove(force=True)
                print(f"✅ Container {container_name} removed")
            except:
                pass  # Container might not exist, that's fine
            
            # Recreate container using docker-compose
            print(f"\n▶️  Recreating container: {container_name} using docker-compose")
            import subprocess
            
            # Determine the docker-compose file location
            compose_file = "/home/reynaldineo/sister/fp/group/docker-compose.yaml"
            
            result = subprocess.run(
                ["docker-compose", "-f", compose_file, "up", "-d", container_name],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"✅ Container {container_name} recreated and started")
                
                # Wait for MySQL to be ready
                print(f"⏳ Waiting for MySQL to be ready...")
                time.sleep(10)
                
                # Rejoin the group replication
                self.rejoin_node_to_cluster(container_name)
                
                return True
            else:
                print(f"❌ Error recreating container: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting container: {e}")
            return False

    def rejoin_node_to_cluster(self, container_name):
        """Rejoin a node to the group replication cluster"""
        try:
            # Find the node name from container name
            node_name = None
            for name, config in self.nodes.items():
                if config['container'] == container_name:
                    node_name = name
                    break
            
            if not node_name:
                print(f"⚠️  Could not find node config for container {container_name}")
                return False
            
            print(f"🔄 Rejoining {node_name} to cluster...")
            
            with self.get_connection(node_name, silent=True) as conn:
                if not conn:
                    print(f"⚠️  Could not connect to {node_name}, may need manual rejoin")
                    return False
                
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("START GROUP_REPLICATION;")
                    conn.commit()
                    print(f"✅ {node_name} rejoined the cluster")
                    return True
                except Error as e:
                    # Error 3093 means group is already running - node auto-rejoined
                    if e.errno == 3093:
                        print(f"✅ {node_name} already in cluster (auto-rejoined)")
                        return True
                    else:
                        print(f"⚠️  Error rejoining cluster: {e}")
                        return False
                
        except Exception as e:
            print(f"⚠️  Exception during rejoin: {e}")
            return False

    def display_final_stats(self) -> None:
        """Display comprehensive final statistics."""
        print(f"\n{'='*80}")
        print("📈 FINAL STATISTICS")
        print(f"{'='*80}")
        
        self._print_basic_stats()
        self._print_failover_metrics()
        self._print_error_breakdown()
        
        print(f"{'='*80}\n")
    
    def _print_basic_stats(self) -> None:
        """Print basic workload statistics."""
        stats = self.workload_stats
        print(f"Total Insert Attempts: {stats['total_attempts']}")
        print(f"Successful Inserts: {stats['successful_inserts']}")
        print(f"Failed Inserts: {stats['failed_inserts']}")
        
        if stats['total_attempts'] > 0:
            success_rate = (stats['successful_inserts'] / stats['total_attempts'] * 100)
            print(f"Success Rate: {success_rate:.2f}%")
    
    def _print_failover_metrics(self) -> None:
        """Print failover-specific metrics."""
        if self.failover_start_time and self.failover_end_time:
            duration = self.failover_end_time - self.failover_start_time
            lost_transactions = sum(self.workload_stats['errors'].values())
            
            print(f"\n⏱️  Failover Metrics:")
            print(f"Failover Duration: {duration:.2f} seconds")
            print(f"Transactions Lost During Failover: {lost_transactions}")
    
    def _print_error_breakdown(self) -> None:
        """Print breakdown of errors by type."""
        if self.workload_stats['errors']:
            print(f"\n❌ Errors Breakdown:")
            for error_type, count in self.workload_stats['errors'].items():
                print(f"  - {error_type}: {count}")

    def verify_data_consistency(self) -> None:
        """Verify data consistency across all nodes in the cluster."""
        print("\n🔍 Verifying data consistency across nodes...")
        
        counts = self._collect_transaction_counts()
        self._display_transaction_counts(counts)
        self._check_consistency(counts)
    
    def _collect_transaction_counts(self) -> Dict[str, Any]:
        """Collect transaction counts from all nodes."""
        counts = {}
        for node_name in self.nodes.keys():
            with self.get_connection(node_name, silent=True) as conn:
                if conn:
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT COUNT(*) as count FROM transactions")
                            result = cursor.fetchone()
                            counts[node_name] = result[0]
                    except Error as e:
                        print(f"❌ Error fetching transaction count from {node_name}: {e}")
                        counts[node_name] = None
        return counts
    
    def _display_transaction_counts(self, counts: Dict[str, Any]) -> None:
        """Display transaction counts for each node."""
        print("\n📊 Transaction counts per node:")
        for node, count in counts.items():
            print(f"  {node}: {count}")
    
    def _check_consistency(self, counts: Dict[str, Any]) -> None:
        """Check if all nodes have the same transaction count."""
        values = [v for v in counts.values() if v is not None]
        if len(set(values)) == 1 and len(values) == len(self.nodes):
            print("\n✅ Data is consistent across all nodes!")
        else:
            print("\n⚠️  Data inconsistency detected!")
    
    def run_test(self) -> None:
        """Execute the complete failover test workflow."""
        self._print_test_header()
        
        # Validate initial cluster state
        primary_node = self._validate_initial_state()
        if not primary_node:
            return
        
        # Setup and start workload
        if not self._setup_and_start_workload():
            return
        
        # Perform failover test
        primary_container = self.nodes[primary_node]['container']
        new_primary = self._execute_failover(primary_node, primary_container)
        
        # Continue workload and recover
        self._continue_workload_post_failover()
        self._recover_failed_node(primary_container)
        
        # Finalize test
        self._finalize_test()
        
        print("\n" + "="*80)
        print("✅ TEST COMPLETED")
        print("="*80 + "\n")
    
    def _print_test_header(self) -> None:
        """Print test header."""
        print("\n" + "="*80)
        print("🚀 MySQL GROUP REPLICATION - PRIMARY FAILOVER TEST")
        print("="*80)
    
    def _validate_initial_state(self) -> Optional[str]:
        """Validate initial cluster state and identify primary."""
        print("\n📋 Step 1: Check initial Group Replication status")
        self.display_group_status("Initial Group Status")
        
        print("\n📋 Step 2: Identify current primary node")
        primary_node, _ = self.get_primary_node()
        
        if primary_node:
            print(f"✅ Current PRIMARY: {primary_node} (Port: {self.nodes[primary_node]['port']})")
        else:
            print("❌ No primary node found!")
        
        return primary_node
    
    def _setup_and_start_workload(self) -> bool:
        """Setup database and start workload thread."""
        print("\n📋 Step 3: Setup test database")
        if not self.setup_test_database():
            return False
        
        print("\n📋 Step 4: Start continuous workload")
        self.workload_running = True
        workload_thread = threading.Thread(target=self.continuous_workload, daemon=True)
        workload_thread.start()
        
        print(f"\n⏳ Letting workload run for {INITIAL_WORKLOAD_DURATION} seconds...")
        time.sleep(INITIAL_WORKLOAD_DURATION)
        return True
    
    def _execute_failover(self, primary_node: str, primary_container: str) -> Optional[str]:
        """Execute the failover by stopping primary and waiting for new election."""
        print("\n📋 Step 5: Simulate PRIMARY node failure")
        print(f"\n⚠️  Stopping PRIMARY node: {primary_node}")
        self.stop_container(primary_container)
        
        print("\n📋 Step 6: Observe failover process")
        print("⏳ Waiting for new primary election...")
        time.sleep(3)
        
        new_primary = self._monitor_primary_election(primary_node)
        
        time.sleep(2)
        self.display_group_status("Status After Failover")
        return new_primary
    
    def _monitor_primary_election(self, old_primary: str) -> Optional[str]:
        """Monitor and wait for new primary election."""
        elapsed = 0
        
        while elapsed < FAILOVER_MAX_WAIT:
            new_primary_node, _ = self.get_primary_node()
            
            if new_primary_node and new_primary_node != old_primary:
                print(f"\n✅ NEW PRIMARY ELECTED: {new_primary_node} "
                      f"(Port: {self.nodes[new_primary_node]['port']})")
                return new_primary_node
            elif new_primary_node:
                print(f"⏳ Still waiting... (current primary check: {new_primary_node})")
            else:
                print(f"⏳ No primary available yet... (elapsed: {elapsed}s)")
            
            time.sleep(FAILOVER_CHECK_INTERVAL)
            elapsed += FAILOVER_CHECK_INTERVAL
        
        return self._handle_election_timeout()
    
    def _handle_election_timeout(self) -> Optional[str]:
        """Handle scenario when election times out."""
        print("\n⚠️  No new primary detected within timeout, checking current state...")
        final_primary, _ = self.get_primary_node()
        
        if final_primary:
            print(f"✅ Found PRIMARY: {final_primary} (Port: {self.nodes[final_primary]['port']})")
            return final_primary
        else:
            print("❌ No primary node is currently active!")
            return None
    
    def _continue_workload_post_failover(self) -> None:
        """Continue workload after failover."""
        print(f"\n⏳ Continuing workload on new primary for {POST_FAILOVER_WORKLOAD_DURATION} seconds...")
        time.sleep(POST_FAILOVER_WORKLOAD_DURATION)
    
    def _recover_failed_node(self, container_name: str) -> None:
        """Recover the failed node."""
        print("\n📋 Step 7: Restart old primary node")
        self.start_container(container_name)
        
        print(f"\n⏳ Waiting for node to rejoin cluster...")
        time.sleep(CLUSTER_REJOIN_WAIT)
        
        self.display_group_status("Final Group Status")
    
    def _finalize_test(self) -> None:
        """Stop workload and display final results."""
        print("\n📋 Step 8: Stopping workload")
        self.workload_running = False
        time.sleep(1)  # Allow thread to finish
        
        self.display_final_stats()
        
        print("\n📋 Step 9: Verify data consistency")
        time.sleep(CONSISTENCY_CHECK_WAIT)
        self.verify_data_consistency()


def main():
    """Main entry point"""
    try:
        test = GroupReplicationFailoverTest()
        test.run_test()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()