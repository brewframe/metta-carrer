"""Set a new password from the server's command line. For the case where the ONLY admin forgot the password.
    python -m metta.reset_password --email admin@sekolah.sch.id
The password is asked interactively (hidden). All sessions of that account are ended."""
import argparse, getpass, sys
from .db import DB, init_db
from .security import check_password, hash_password
from .api.auth import clean_email

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter); ap.add_argument("--email", required=True)
    a = ap.parse_args(argv)
    try: email = clean_email(a.email)
    except ValueError: sys.exit("Invalid email address")
    pw = getpass.getpass("New password: ")
    if pw != getpass.getpass("Repeat password: "): sys.exit("The two passwords are different")
    init_db(); d = DB()
    try:
        u = d.one("SELECT * FROM users WHERE email=?", email)
        if not u: sys.exit("No account with this email")
        err = check_password(pw, email, u["name"], staff=u["role"] != "student")
        if err: sys.exit("Password rejected: " + err)
        d.run("UPDATE users SET password_hash=?, must_change_password=0 WHERE id=?", hash_password(pw), u["id"]); d.run("DELETE FROM sessions WHERE user_id=?", u["id"])
        d.run("INSERT INTO audit_log(actor_id,action,detail) VALUES(NULL,'password_reset_cli',?)", str(u["id"])); d.commit(); print("Password changed for", email)
    finally: d.close()

if __name__ == "__main__": main()
