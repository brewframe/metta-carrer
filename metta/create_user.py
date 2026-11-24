"""Create an account from the command line, e.g. the very first admin on a new server.
    python -m metta.create_user --email kepala@sekolah.sch.id --name "Nama Admin" --role admin
The password is asked interactively (hidden). For scripts: add --password-stdin and pipe it in."""
import argparse, getpass, sys
from .db import DB, init_db
from .security import check_password, hash_password
from .api.auth import clean_email

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--email", required=True); ap.add_argument("--name", required=True)
    ap.add_argument("--role", required=True, choices=["student", "teacher", "alumni", "admin"])
    ap.add_argument("--major", default="TKJ", choices=["AK", "TKJ"]); ap.add_argument("--class-name", default="")
    ap.add_argument("--password-stdin", action="store_true", help="read the password from standard input")
    a = ap.parse_args(argv)
    try: email = clean_email(a.email)
    except ValueError: sys.exit("Invalid email address")
    if a.password_stdin: pw = sys.stdin.readline().rstrip("\r\n")
    else:
        pw = getpass.getpass("Password: ")
        if pw != getpass.getpass("Repeat password: "): sys.exit("The two passwords are different")
    err = check_password(pw, email, a.name, staff=a.role != "student")
    if err: sys.exit("Password rejected: " + err)
    init_db(); d = DB()
    try:
        if d.one("SELECT 1 x FROM users WHERE email=?", email): sys.exit("This email is already registered")
        uid = d.run("INSERT INTO users(email,name,password_hash,role) VALUES(?,?,?,?)", email, a.name.strip(), hash_password(pw), a.role)
        if a.role == "student": d.run("INSERT INTO student_profiles(user_id,school,major,class_name) VALUES(?,?,?,?)", uid, "SMK Metta Maitreya", a.major, a.class_name)
        d.run("INSERT INTO audit_log(actor_id,action,detail) VALUES(NULL,'user_create_cli',?)", f"{uid}:{a.role}"); d.commit()
    finally: d.close()
    print(f"Created {a.role} account {email}")

if __name__ == "__main__": main()
