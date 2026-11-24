@echo off
REM Hapus database LOKAL lalu mulai lagi dengan data demo yang bersih. Hanya untuk latihan presentasi.
echo Ini akan MENGHAPUS semua data di metta.db pada komputer ini dan membuat data demo baru.
set /p OK=Ketik YA lalu Enter untuk lanjut:
if /I not "%OK%"=="YA" (
  echo Dibatalkan. Tidak ada yang dihapus.
  exit /b 1
)
del /q metta.db metta.db-wal metta.db-shm 2>nul
call run_dev.bat
