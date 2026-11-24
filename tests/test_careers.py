"""Data 100 karier: lengkap, konsisten, dua bahasa, dan aman di-upgrade dari database lama."""
import os, sqlite3, subprocess, sys, tempfile, unittest
from tests.support import ROOT

TAGS_I = {"technology", "finance", "business", "design", "data", "people"}
TAGS_S = {"analytical", "problem_solving", "detail", "logical", "communication", "creativity", "collaboration", "technical"}

def seeded(path):
    env = dict(os.environ, METTA_DB=path)
    subprocess.run([sys.executable, "-m", "metta.seed"], cwd=ROOT, env=env, check=True, capture_output=True)
    c = sqlite3.connect(path); c.row_factory = sqlite3.Row; return c

class CareerData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = os.path.join(tempfile.mkdtemp(), "c.db"); cls.c = seeded(cls.path)

    def test_100_careers_and_field_counts(self):
        self.assertEqual(self.c.execute("SELECT count(*) FROM careers").fetchone()[0], 100)
        got = dict(self.c.execute("SELECT category, count(*) FROM careers GROUP BY 1").fetchall())
        self.assertEqual(got, {"Technology": 39, "Finance": 27, "Business": 10, "Industry": 6, "Creative": 5, "Health": 4, "Energy": 4, "Service": 3, "Education": 2})

    def test_every_career_is_complete(self):
        for r in self.c.execute("SELECT * FROM careers"):
            for f in ("name", "description", "responsibilities", "education_path", "example_projects", "growth"):
                self.assertTrue(len(r[f]) >= (4 if f == "name" else 10), (r["name"], f))
            self.assertTrue(set(r["interest_tags"].split(",")) <= TAGS_I and r["interest_tags"], r["name"])
            self.assertTrue(set(r["strength_tags"].split(",")) <= TAGS_S and r["strength_tags"], r["name"])
            self.assertTrue(set(r["majors"].split(",")) <= {"AK", "TKJ"} and r["majors"], r["name"])
            n = self.c.execute("SELECT count(*) FROM career_skills WHERE career_id=?", (r["id"],)).fetchone()[0]
            self.assertGreaterEqual(n, 2, r["name"])

    def test_every_career_and_skill_has_indonesian(self):
        for r in self.c.execute("SELECT id,name FROM careers"):
            for f in ("name", "description", "responsibilities", "education_path", "example_projects", "growth"):
                v = self.c.execute("SELECT value FROM translations WHERE entity='career' AND entity_id=? AND field=? AND lang='id'", (r["id"], f)).fetchone()
                self.assertTrue(v and v[0], (r["name"], f))
        for r in self.c.execute("SELECT id,name FROM skills WHERE id IN (SELECT skill_id FROM career_skills)"):
            v = self.c.execute("SELECT value FROM translations WHERE entity='skill' AND entity_id=? AND field='name' AND lang='id'", (r["id"],)).fetchone()
            self.assertTrue(v and v[0], r["name"])

    def test_trend_and_new_flags(self):
        self.assertEqual(self.c.execute("SELECT count(*) FROM careers WHERE trend=1").fetchone()[0], 25)
        self.assertEqual(self.c.execute("SELECT count(*) FROM careers WHERE is_new=1").fetchone()[0], 50)

    def test_seed_twice_changes_nothing(self):
        before = [self.c.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("careers", "skills", "career_skills", "translations", "questions", "companies")]
        c2 = seeded(self.path)
        after = [c2.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("careers", "skills", "career_skills", "translations", "questions", "companies")]
        self.assertEqual(before, after)
        self.assertEqual(before[-1], 55)

class UpgradeOldDb(unittest.TestCase):
    def test_old_ten_career_db_is_upgraded_without_losing_data(self):
        path = os.path.join(tempfile.mkdtemp(), "old.db")
        c = seeded(path)
        # meniru database versi lama: hanya 10 karier, tanpa kolom trend/is_new, ada edit admin dan ada siswa
        keep = [r[0] for r in c.execute("SELECT id FROM careers ORDER BY id LIMIT 10")]
        c.execute("PRAGMA foreign_keys=OFF")
        c.execute("DELETE FROM career_skills WHERE career_id NOT IN (%s)" % ",".join(map(str, keep)))
        c.execute("DELETE FROM translations WHERE entity='career' AND entity_id NOT IN (%s)" % ",".join(map(str, keep)))
        c.execute("DELETE FROM careers WHERE id NOT IN (%s)" % ",".join(map(str, keep)))
        c.execute("UPDATE careers SET description='EDIT ADMIN' WHERE id=?", (keep[0],))
        c.execute("INSERT INTO users(email,name,password_hash,role) VALUES('x@y.z','Siswa Lama','x','student')")
        c.commit(); c.close()
        c = seeded(path)
        self.assertEqual(c.execute("SELECT count(*) FROM careers").fetchone()[0], 100)
        self.assertEqual(c.execute("SELECT description FROM careers WHERE id=?", (keep[0],)).fetchone()[0], "EDIT ADMIN")   # edit admin tidak tertimpa
        self.assertEqual(c.execute("SELECT count(*) FROM users WHERE email='x@y.z'").fetchone()[0], 1)

if __name__ == "__main__":
    unittest.main()
