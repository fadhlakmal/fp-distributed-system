import mysql.connector
import time
import threading

# Konfigurasi Koneksi
db_config = {'user': 'root', 'password': 'pass', 'database': 'testdb'}
primary_conf = {**db_config, 'host': '127.0.0.1', 'port': 3306}
replica1_conf = {**db_config, 'host': '127.0.0.1', 'port': 3307}
replica2_conf = {**db_config, 'host': '127.0.0.1', 'port': 3308}

def setup_database():
    """Membuat database dan tabel di Primary"""
    try:
        conn = mysql.connector.connect(user='root', password='pass', host='127.0.0.1', port=3306)
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS testdb")
        cursor.execute("USE testdb")
        cursor.execute("DROP TABLE IF EXISTS scenario1")
        cursor.execute("""
            CREATE TABLE scenario1 (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data VARCHAR(100),
                created_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3)
            )
        """)
        conn.commit()
        print("[INFO] Database dan Tabel siap.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Setup gagal: {e}")

def measure_lag(name, config, target_id, start_time):
    """
    Melakukan polling (cek berulang) ke Replica sampai data ditemukan
    untuk menghitung durasi keterlambatan.
    """
    try:
        conn = mysql.connector.connect(**config)
        # Agar setiap select membaca data terbaru, matikan autocommit atau commit manual
        conn.autocommit = True
        cursor = conn.cursor()

        data_found = False
        timeout_seconds = 10

        while (time.time() - start_time) < timeout_seconds:
            # PENTING: Commit ini memaksa refresh snapshot data!
            # Tanpa ini, kita terjebak melihat data lama (Repeatable Read)
            conn.commit()

            cursor.execute(f"SELECT id, created_at FROM scenario1 WHERE id = {target_id}")
            row = cursor.fetchone()

            if row:
                arrival_time = time.time()
                lag_seconds = arrival_time - start_time
                lag_ms = lag_seconds * 1000

                print(f"✅ {name}: Data DITERIMA.")
                print(f"   ⏱️  Lag/Keterlambatan: {lag_ms:.2f} ms ({lag_seconds:.4f} detik)")
                data_found = True
                break

            time.sleep(0.001)

        if not data_found:
            print(f"❌ {name}: Data TIDAK DITERIMA setelah {timeout_seconds} detik (Timeout).")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ {name} Error: {e}")

def run_scenario():
    setup_database()

    conn_primary = mysql.connector.connect(**primary_conf)
    cursor_primary = conn_primary.cursor()

    print("\n--- MULAI SKENARIO 1: INSERT 1000 ROWS ---")

    # 1. Insert 999 dummy rows (Pemanasan & Load)
    print("[ACTION] Insert 999 dummy rows...")
    for i in range(999):
        cursor_primary.execute("INSERT INTO scenario1 (data) VALUES ('dummy')")
    conn_primary.commit()

    # 2. Insert row ke-1000 (Target Pengujian)
    print("[ACTION] Insert row ke-1000 (TARGET)...")
    cursor_primary.execute("INSERT INTO scenario1 (data) VALUES ('TARGET_DATA')")

    # COMMIT PENTING: Waktu start dihitung tepat setelah commit berhasil di Primary
    conn_primary.commit()
    insert_finish_time = time.time()
    last_id = cursor_primary.lastrowid

    print(f"[PRIMARY] Insert selesai (ID: {last_id}). Menunggu Replica...")

    # 3. Ukur Lag di Replica secara Paralel
    t1 = threading.Thread(target=measure_lag, args=("Replica 1", replica1_conf, last_id, insert_finish_time))
    t2 = threading.Thread(target=measure_lag, args=("Replica 2", replica2_conf, last_id, insert_finish_time))

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print("\n--- SELESAI ---")

if __name__ == "__main__":
    run_scenario()