"""Jalankan server Metta dengan skema yang memakai op_now() (waktu operasi) agar database dasar cocok untuk artifact."""
import sys, datetime
sys.path.insert(0, "/home/claude/metta-career-app")
import metta.db as D
D.SCHEMA = D.SCHEMA.replace("(datetime('now'))", "(op_now())")
_orig = D.DB.__init__
def _init(self, lang="en"):
    _orig(self, lang)
    self.conn.create_function("op_now", 0, lambda: datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
D.DB.__init__ = _init
import uvicorn
uvicorn.run("metta.app:app", port=int(sys.argv[1]), log_level="warning")
