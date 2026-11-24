"""Tes Data DU/DI: guru melengkapi data perusahaan, admin menambah dan menghapus."""
import unittest
from .support import Server, Client

AD = ("admin@metta.sch", "Admin#2026!"); ST = ("student@metta.sch", "Student#2026!"); TE = ("teacher@metta.sch", "Teacher#2026!")


class CompanyData(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.srv = Server(8797, METTA_SEED_DEMO=1).start()
    @classmethod
    def tearDownClass(cls): cls.srv.stop()

    def who(self, cred, role=""):
        c = Client(self.srv.base); c.s.headers["X-Lang"] = "en"; self.assertEqual(c.login(*cred, role)[0], 200); return c

    def test_company_fill(self):
        t, adm = self.who(TE), self.who(AD); cs = adm.get("/api/companies")[1]["items"]
        un = [c for c in cs if not c["verified"]][0]; ver = [c for c in cs if c["verified"]][0]
        self.assertEqual(t.put(f"/api/teacher/companies/{un['id']}", {"address": "Jl. Contoh 1, Pekanbaru", "source": ""})[0], 422)
        self.assertEqual(t.put(f"/api/teacher/companies/{un['id']}", {"address": "Jl. Contoh 1, Pekanbaru", "source": "Surat tugas PKL"})[0], 200)
        after = [c for c in adm.get("/api/companies")[1]["items"] if c["id"] == un["id"]][0]; self.assertEqual(after["address"], "Jl. Contoh 1, Pekanbaru"); self.assertFalse(after["verified"])
        self.assertEqual(t.put(f"/api/teacher/companies/{ver['id']}", {"address": "x", "source": "abc"})[0], 403)
        self.assertEqual(self.who(ST).put(f"/api/teacher/companies/{un['id']}", {"address": "x", "source": "abc"})[0], 403)
        st, r = adm.post("/api/admin/companies", {"name": "PT Baru Maju", "address": "Jl. A"}); self.assertEqual(st, 200)
        self.assertEqual(adm.delete(f"/api/admin/companies/{r['id']}")[0], 200)


if __name__ == "__main__":
    unittest.main()
