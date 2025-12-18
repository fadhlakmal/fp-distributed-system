import mysql.connector
import time
import threading
import random

TOTAL_ROWS   = 1000  
PAYLOAD_SIZE = 5000  

# Konfigurasi Koneksi Database
db_config = {'user': 'root', 'password': 'pass', 'database': 'testdb'}
primary_conf = {**db_config, 'host': '127.0.0.1', 'port': 3306}
replica1_conf = {**db_config, 'host': '127.0.0.1', 'port': 3307}
replica2_conf = {**db_config, 'host': '127.0.0.1', 'port': 3308}

# Contoh Teks Acak
TEXT_SAMPLES = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. ",
    "[LOG-INFO] User transaction SUCCESS id=8821. ",
    "{'json_data': {'id': 123, 'status': 'active', 'meta': 'data'}}. ",
    "SELECT * FROM transactions WHERE status = 'pending'; ",
    "Paket Anda sedang dalam perjalanan menuju Jakarta. "
]

def generate_random_payload(target_size):
    """Membuat teks acak sesuai ukuran yang diminta"""
    result = []
    current_size = 0
    while current_size < target_size:
        part = random.choice(TEXT_SAMPLES)
        result.append(part)
        current_size += len(part)
    return "".join(result)

def setup_database():
    """Reset Database"""
    try:
        conn = mysql.connector.connect(user='root', password='pass', host='127.0.0.1', port=3306)
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS testdb")
        cursor.execute("USE testdb")
        cursor.execute("DROP TABLE IF EXISTS scenario1")
        cursor.execute("""
            CREATE TABLE scenario1 (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data LONGTEXT, 
                created_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3)
            )
        """)
        conn.commit()
        print(f"[INFO] Database siap. Target Uji: {TOTAL_ROWS} Baris.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Setup gagal: {e}")

def measure_lag(name, config, target_id, start_time):
    """Mengukur Lag"""
    try:
        conn = mysql.connector.connect(**config)
        conn.autocommit = True
        cursor = conn.cursor()
        data_found = False
        timeout = 30 # Timeout diperlama untuk jaga-jaga jika data banyak

        while (time.time() - start_time) < timeout:
            conn.commit()
            cursor.execute(f"SELECT id FROM scenario1 WHERE id = {target_id}")
            if cursor.fetchone():
                lag = (time.time() - start_time) * 1000
                print(f"✅ {name}: Data masuk dalam {lag:.2f} ms")
                data_found = True
                break
            time.sleep(0.001)

        if not data_found:
            print(f"❌ {name}: Timeout menunggu data.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ {name} Error: {e}")

def verify_integrity(name, config, target_id, expected_content, total_expected_rows):
    """Memeriksa jumlah baris dan isi konten"""
    print(f"\n[AUDIT] Memeriksa Integritas Data di {name}...")
    try:
        conn = mysql.connector.connect(**config)
        conn.autocommit = True 
        cursor = conn.cursor()

        # 1. Cek Jumlah Baris
        cursor.execute("SELECT COUNT(*) FROM scenario1")
        row_count = cursor.fetchone()[0]
        
        if row_count == total_expected_rows:
            print(f"   Shape OK : Jumlah baris sesuai ({row_count}).")
        else:
            print(f"   Shape FAIL : Harapan {total_expected_rows}, tapi ditemukan {row_count}!")

        # 2. Cek Konten
        cursor.execute(f"SELECT data FROM scenario1 WHERE id = {target_id}")
        result = cursor.fetchone()
        
        if result and result[0] == expected_content:
            print(f"   Content OK : Isi data identik.")
        else:
            print(f"   Content FAIL : Isi data rusak atau tidak ditemukan!")
        
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"   [ERROR] Verifikasi gagal: {e}")

def run_scenario():
    setup_database()
    conn_primary = mysql.connector.connect(**primary_conf)
    cursor_primary = conn_primary.cursor()

    # Hitung jumlah dummy (Total dikurang 1 target utama)
    dummy_count = TOTAL_ROWS - 1
    
    print(f"\n--- MULAI SKENARIO: {TOTAL_ROWS} ROWS (Payload: {PAYLOAD_SIZE} bytes) ---")
    
    # Generate Payload
    base_payload = generate_random_payload(PAYLOAD_SIZE)
    target_payload = generate_random_payload(PAYLOAD_SIZE) # Payload unik untuk target

    # 1. Insert Dummy Rows (Looping otomatis berdasarkan variabel)
    if dummy_count > 0:
        print(f"[ACTION] Insert {dummy_count} dummy rows...")
        query = "INSERT INTO scenario1 (data) VALUES (%s)"
        for _ in range(dummy_count):
            cursor_primary.execute(query, (base_payload,))
        conn_primary.commit()

    # 2. Insert Target (Row Terakhir)
    print(f"[ACTION] Insert TARGET data (Row ke-{TOTAL_ROWS})...")
    cursor_primary.execute("INSERT INTO scenario1 (data) VALUES (%s)", (target_payload,))
    conn_primary.commit() 

    # Waktu mulai
    start_time = time.time()
    last_id = cursor_primary.lastrowid

    print(f"[PRIMARY] Insert selesai. Menunggu Replica...")

    # 3. Ukur Lag
    t1 = threading.Thread(target=measure_lag, args=("Replica 1", replica1_conf, last_id, start_time))
    t2 = threading.Thread(target=measure_lag, args=("Replica 2", replica2_conf, last_id, start_time))
    t1.start(); t2.start()
    t1.join(); t2.join()

    # 4. Verifikasi (Menggunakan variabel TOTAL_ROWS)
    verify_integrity("Replica 1", replica1_conf, last_id, target_payload, TOTAL_ROWS)
    verify_integrity("Replica 2", replica2_conf, last_id, target_payload, TOTAL_ROWS)

    print("\n--- SELESAI ---")

if __name__ == "__main__":
    run_scenario()