#!/usr/bin/env python3
"""
Real-time Group Replication Monitor
Monitors the status of Group Replication cluster in real-time
"""

import mysql.connector
from mysql.connector import Error
import time
import os
from datetime import datetime

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def get_connection(port):
    """Create MySQL connection"""
    try:
        return mysql.connector.connect(
            host='localhost',
            port=port,
            user='root',
            password='pass',
            database='mysql'
        )
    except Error:
        return None

def get_group_status(port):
    """Get Group Replication status"""
    conn = get_connection(port)
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get group members
        cursor.execute("""
            SELECT 
                MEMBER_ID,
                MEMBER_HOST,
                MEMBER_PORT,
                MEMBER_STATE,
                MEMBER_ROLE,
                MEMBER_VERSION
            FROM performance_schema.replication_group_members
            ORDER BY MEMBER_ROLE DESC, MEMBER_PORT
        """)
        members = cursor.fetchall()
        
        # Get replication status
        cursor.execute("""
            SELECT 
                CHANNEL_NAME,
                SERVICE_STATE,
                COUNT_TRANSACTIONS_IN_QUEUE as QUEUED,
                COUNT_TRANSACTIONS_CHECKED as CHECKED,
                COUNT_CONFLICTS_DETECTED as CONFLICTS
            FROM performance_schema.replication_group_member_stats
        """)
        stats = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {'members': members, 'stats': stats}
    except Error:
        if conn:
            conn.close()
        return None

def display_status():
    """Display real-time status"""
    # Try to get status from any available node
    status = None
    active_port = None
    
    for port in [3306, 3307, 3308]:
        status = get_group_status(port)
        if status:
            active_port = port
            break
    
    clear_screen()
    
    print("=" * 100)
    print(f"🔍 MYSQL GROUP REPLICATION MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)
    
    if not status:
        print("\n❌ Unable to connect to any cluster node")
        print("\nNode Status:")
        for port in [3306, 3307, 3308]:
            node = f"node{port-3305}"
            conn = get_connection(port)
            if conn:
                print(f"  ✅ {node} (port {port}): Online")
                conn.close()
            else:
                print(f"  ❌ {node} (port {port}): Offline")
        return
    
    print(f"\n📡 Monitoring from: localhost:{active_port}")
    
    # Display cluster members
    print("\n" + "=" * 100)
    print("👥 CLUSTER MEMBERS")
    print("=" * 100)
    
    if status['members']:
        print(f"{'Node':<12} {'Host':<20} {'Port':<8} {'State':<15} {'Role':<12}")
        print("-" * 100)
        
        for member in status['members']:
            # Determine node name
            node_num = member['MEMBER_PORT'] - 3305
            node_name = f"node{node_num}"
            
            # Color coding for state
            state = member['MEMBER_STATE']
            if state == 'ONLINE':
                state_display = f"🟢 {state}"
            elif state == 'RECOVERING':
                state_display = f"🟡 {state}"
            else:
                state_display = f"🔴 {state}"
            
            # Color coding for role
            role = member['MEMBER_ROLE']
            if role == 'PRIMARY':
                role_display = f"👑 {role}"
            else:
                role_display = f"   {role}"
            
            print(f"{node_name:<12} {member['MEMBER_HOST']:<20} {member['MEMBER_PORT']:<8} "
                  f"{state_display:<20} {role_display:<12}")
    else:
        print("No members found")
    
    # Display replication statistics
    print("\n" + "=" * 100)
    print("📊 REPLICATION STATISTICS")
    print("=" * 100)
    
    if status['stats']:
        for stat in status['stats']:
            print(f"\nChannel: {stat['CHANNEL_NAME']}")
            print(f"  Service State: {stat['SERVICE_STATE']}")
            print(f"  Transactions in Queue: {stat['QUEUED']}")
            print(f"  Transactions Checked: {stat['CHECKED']}")
            print(f"  Conflicts Detected: {stat['CONFLICTS']}")
    
    # Check individual node connectivity
    print("\n" + "=" * 100)
    print("🔌 NODE CONNECTIVITY")
    print("=" * 100)
    
    for port in [3306, 3307, 3308]:
        node = f"node{port-3305}"
        conn = get_connection(port)
        if conn:
            # Get uptime
            try:
                cursor = conn.cursor()
                cursor.execute("SHOW STATUS LIKE 'Uptime'")
                uptime = cursor.fetchone()[1]
                uptime_hours = int(uptime) / 3600
                cursor.close()
                print(f"  ✅ {node:<8} (port {port}): Online - Uptime: {uptime_hours:.2f}h")
            except:
                print(f"  ✅ {node:<8} (port {port}): Online")
            conn.close()
        else:
            print(f"  ❌ {node:<8} (port {port}): Offline")
    
    print("\n" + "=" * 100)
    print("Press Ctrl+C to exit")
    print("=" * 100)

def main():
    """Main monitoring loop"""
    print("\n🚀 Starting MySQL Group Replication Monitor...")
    print("This will refresh every 2 seconds\n")
    
    try:
        while True:
            display_status()
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n\n✋ Monitor stopped by user")
        print("Goodbye! 👋\n")

if __name__ == "__main__":
    main()