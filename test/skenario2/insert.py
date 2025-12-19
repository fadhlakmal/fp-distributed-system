#!/usr/bin/env python3
"""
Manual Failover Test - Interactive Mode
Allows manual control of failover testing process
"""

import mysql.connector
from mysql.connector import Error
import docker
import sys
from datetime import datetime

class ManualFailoverTest:
    def __init__(self):
        self.client = docker.from_env()
        self.nodes = {
            'node1': {'host': 'localhost', 'port': 3306, 'container': 'node1'},
            'node2': {'host': 'localhost', 'port': 3307, 'container': 'node2'},
            'node3': {'host': 'localhost', 'port': 3308, 'container': 'node3'}
        }
        self.user = 'root'
        self.password = 'pass'

    def get_connection(self, node_name):
        """Create MySQL connection"""
        node = self.nodes[node_name]
        try:
            return mysql.connector.connect(
                host=node['host'],
                port=node['port'],
                user=self.user,
                password=self.password
            )
        except Error as e:
            print(f"❌ Error: {e}")
            return None

    def show_status(self):
        """Show cluster status"""
        print("\n" + "="*80)
        print("📊 CLUSTER STATUS")
        print("="*80)
        
        for node_name in ['node1', 'node2', 'node3']:
            conn = self.get_connection(node_name)
            if conn:
                try:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT 
                            MEMBER_HOST,
                            MEMBER_PORT,
                            MEMBER_STATE,
                            MEMBER_ROLE
                        FROM performance_schema.replication_group_members
                        WHERE MEMBER_PORT = %s
                    """, (self.nodes[node_name]['port'],))
                    
                    result = cursor.fetchone()
                    if result:
                        role_icon = "👑" if result['MEMBER_ROLE'] == 'PRIMARY' else "  "
                        state_icon = "🟢" if result['MEMBER_STATE'] == 'ONLINE' else "🔴"
                        print(f"{state_icon} {role_icon} {node_name}: {result['MEMBER_STATE']:<12} - {result['MEMBER_ROLE']}")
                    else:
                        print(f"🔴    {node_name}: Not in group")
                    
                    cursor.close()
                    conn.close()
                except Error as e:
                    print(f"🔴    {node_name}: Error - {e}")
                    if conn:
                        conn.close()
            else:
                print(f"🔴    {node_name}: Offline")
        
        print("="*80 + "\n")

    def show_group_members(self):
        """Show all group members"""
        print("\n" + "="*80)
        print("👥 GROUP MEMBERS")
        print("="*80)
        
        conn = None
        for node_name in ['node1', 'node2', 'node3']:
            conn = self.get_connection(node_name)
            if conn:
                break
        
        if not conn:
            print("❌ Cannot connect to any node")
            return
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT 
                    MEMBER_ID,
                    MEMBER_HOST,
                    MEMBER_PORT,
                    MEMBER_STATE,
                    MEMBER_ROLE
                FROM performance_schema.replication_group_members
                ORDER BY MEMBER_ROLE DESC, MEMBER_PORT
            """)
            
            members = cursor.fetchall()
            
            print(f"{'Host':<20} {'Port':<8} {'State':<15} {'Role':<12}")
            print("-"*80)
            
            for member in members:
                role_icon = "👑" if member['MEMBER_ROLE'] == 'PRIMARY' else "  "
                print(f"{role_icon} {member['MEMBER_HOST']:<18} {member['MEMBER_PORT']:<8} "
                      f"{member['MEMBER_STATE']:<15} {member['MEMBER_ROLE']}")
            
            cursor.close()
            conn.close()
        except Error as e:
            print(f"❌ Error: {e}")
            if conn:
                conn.close()
        
        print("="*80 + "\n")

    def stop_node(self, node_name):
        """Stop a node"""
        if node_name not in self.nodes:
            print(f"❌ Invalid node: {node_name}")
            return
        
        try:
            container = self.client.containers.get(self.nodes[node_name]['container'])
            print(f"\n🛑 Stopping {node_name}...")
            container.stop()
            print(f"✅ {node_name} stopped at {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"❌ Error: {e}")

    def start_node(self, node_name):
        """Start a node"""
        if node_name not in self.nodes:
            print(f"❌ Invalid node: {node_name}")
            return
        
        try:
            container = self.client.containers.get(self.nodes[node_name]['container'])
            print(f"\n▶️  Starting {node_name}...")
            container.start()
            print(f"✅ {node_name} started at {datetime.now().strftime('%H:%M:%S')}")
            print("⏳ Wait ~10-15 seconds for node to rejoin the group")
        except Exception as e:
            print(f"❌ Error: {e}")

    def restart_node(self, node_name):
        """Restart a node"""
        if node_name not in self.nodes:
            print(f"❌ Invalid node: {node_name}")
            return
        
        try:
            container = self.client.containers.get(self.nodes[node_name]['container'])
            print(f"\n🔄 Restarting {node_name}...")
            container.restart()
            print(f"✅ {node_name} restarted at {datetime.now().strftime('%H:%M:%S')}")
            print("⏳ Wait ~10-15 seconds for node to rejoin the group")
        except Exception as e:
            print(f"❌ Error: {e}")

    def insert_test_data(self, count=10):
        """Insert test data"""
        print(f"\n📝 Inserting {count} test records...")
        
        # Find primary
        primary = None
        for node_name in ['node1', 'node2', 'node3']:
            conn = self.get_connection(node_name)
            if conn:
                try:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT MEMBER_ROLE 
                        FROM performance_schema.replication_group_members
                        WHERE MEMBER_PORT = %s
                    """, (self.nodes[node_name]['port'],))
                    result = cursor.fetchone()
                    if result and result['MEMBER_ROLE'] == 'PRIMARY':
                        primary = node_name
                        cursor.close()
                        conn.close()
                        break
                    cursor.close()
                    conn.close()
                except:
                    if conn:
                        conn.close()
        
        if not primary:
            print("❌ No primary found")
            return
        
        print(f"✅ Using primary: {primary}")
        
        conn = self.get_connection(primary)
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Ensure database exists
            cursor.execute("CREATE DATABASE IF NOT EXISTS testdb")
            cursor.execute("USE testdb")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data VARCHAR(255)
                ) ENGINE=InnoDB
            """)
            
            # Insert data
            success = 0
            for i in range(count):
                try:
                    cursor.execute(
                        "INSERT INTO test_transactions (data) VALUES (%s)",
                        (f"Test data {i+1}",)
                    )
                    conn.commit()
                    success += 1
                except Error as e:
                    print(f"❌ Insert failed: {e}")
            
            cursor.close()
            conn.close()
            
            print(f"✅ Successfully inserted {success}/{count} records")
            
        except Error as e:
            print(f"❌ Error: {e}")
            if conn:
                conn.close()

    def show_data_count(self):
        """Show data count on all nodes"""
        print("\n" + "="*80)
        print("📊 DATA COUNT PER NODE")
        print("="*80)
        
        for node_name in ['node1', 'node2', 'node3']:
            conn = self.get_connection(node_name)
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("USE testdb")
                    cursor.execute("SELECT COUNT(*) FROM test_transactions")
                    count = cursor.fetchone()[0]
                    cursor.close()
                    conn.close()
                    print(f"✅ {node_name}: {count} records")
                except Error:
                    if conn:
                        conn.close()
                    print(f"⚠️  {node_name}: No data or error")
            else:
                print(f"❌ {node_name}: Offline")
        
        print("="*80 + "\n")

    def show_menu(self):
        """Show interactive menu"""
        print("\n" + "="*80)
        print("🎮 MANUAL FAILOVER TEST MENU")
        print("="*80)
        print("1. Show cluster status")
        print("2. Show group members (detailed)")
        print("3. Stop node1 (PRIMARY)")
        print("4. Stop node2")
        print("5. Stop node3")
        print("6. Start node1")
        print("7. Start node2")
        print("8. Start node3")
        print("9. Restart node1")
        print("10. Insert test data")
        print("11. Show data count")
        print("0. Exit")
        print("="*80)

    def run(self):
        """Run interactive test"""
        print("\n🚀 MANUAL FAILOVER TEST - INTERACTIVE MODE")
        print("="*80)
        
        while True:
            self.show_menu()
            choice = input("\nEnter your choice: ").strip()
            
            if choice == '1':
                self.show_status()
            elif choice == '2':
                self.show_group_members()
            elif choice == '3':
                self.stop_node('node1')
            elif choice == '4':
                self.stop_node('node2')
            elif choice == '5':
                self.stop_node('node3')
            elif choice == '6':
                self.start_node('node1')
            elif choice == '7':
                self.start_node('node2')
            elif choice == '8':
                self.start_node('node3')
            elif choice == '9':
                self.restart_node('node1')
            elif choice == '10':
                count = input("How many records to insert? (default: 10): ").strip()
                count = int(count) if count.isdigit() else 10
                self.insert_test_data(count)
            elif choice == '11':
                self.show_data_count()
            elif choice == '0':
                print("\n👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice")
            
            input("\nPress Enter to continue...")

def main():
    try:
        test = ManualFailoverTest()
        test.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()