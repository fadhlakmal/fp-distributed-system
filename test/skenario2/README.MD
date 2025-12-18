# Skenario 2: Primary Failover pada Group Replication

Skenario ini mendemonstrasikan pengaturan kluster Replikasi Grup MySQL, memantau, memasukan data, mensimulasikan kegagalan, dan memulai ulang sistem.

## Prasyarat

- Docker dan Docker Compose terinstal
- Shell Bash

## Langkah-langkah Menjalankan Skenario

1. **Mulai Lingkungan**: Jalankan `up.sh` untuk menjalankan kontainer Docker untuk node MySQL.
   ```
   bash up.sh
   ```

2. **Inisialisasi Database**: Jalankan `db.sh` untuk mengatur skema database dan data awal.
   ```
   bash db.sh
   ```

3. **Pantau Kluster**: Di terminal baru, jalankan `monitor.sh` untuk terus memantau status replikasi grup.
   ```
   bash monitor.sh
   ```

4. **Sisipkan Data**: Di terminal baru lainnya, jalankan `insert.sh` untuk memasukan data uji ke database.
   ```
   bash insert.sh
   ```

5. **Simulasi Kegagalan**: Di terminal baru lagi, jalankan `failure.sh` untuk mensimulasikan kegagalan node di kluster.
   ```
   bash failure.sh
   ```

6. **Mulai Ulang Sistem**: Setelah mengamati kegagalan, jalankan `restart.sh` untuk memulai ulang dan memulihkan kluster.
   ```
   bash restart.sh
   ```

7. **Pembersihan**: Ketika selesai, jalankan `down.sh` untuk menghentikan dan menghapus semua kontainer dan data.
   ```
   bash down.sh
   ```

## Catatan

- Pastikan setiap skrip dijalankan dalam urutan yang sesuai.
- Skrip pemantauan mungkin berjalan tanpa batas; gunakan Ctrl+C untuk menghentikannya.
- Sesuaikan konfigurasi di folder config/ jika diperlukan.
