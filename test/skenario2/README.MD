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

3. **Jalankan Script Scenario**: Jalankan `test.py` untuk menguji failover, dengan mensimulasikan kegagalan salah satu node.
   ```
   python3 test.py
   ```

4. **Pembersihan**: Ketika selesai, jalankan `down.sh` untuk menghentikan dan menghapus semua kontainer dan data.
   ```
   bash down.sh
   ```

## Catatan

- Pastikan setiap skrip dijalankan dalam urutan yang sesuai.
- Skrip pemantauan mungkin berjalan tanpa batas, gunakan Ctrl+C untuk menghentikannya.
