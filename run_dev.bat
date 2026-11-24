@echo off
REM Local development ONLY: creates demo accounts with known passwords. Never use these settings online.
set METTA_SEED_DEMO=1
REM Isi data contoh untuk presentasi setelah server siap (aman dijalankan berkali-kali).
start "" /b python -m metta.demo_data --wait
python -m uvicorn metta.app:app --reload
