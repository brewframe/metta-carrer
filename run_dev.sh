#!/bin/sh
# Local development ONLY: creates demo accounts with known passwords. Never use these settings online.
# Isi data contoh untuk presentasi setelah server siap (aman dijalankan berkali-kali).
python3 -m metta.demo_data --wait &
METTA_SEED_DEMO=1 python3 -m uvicorn metta.app:app --reload
