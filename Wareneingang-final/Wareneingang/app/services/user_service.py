import hashlib
import hmac

from app.db import fetch_one, is_database_configured


ROLE_SECURITY_LEVELS = {
    "Lager": 1,
    "Management": 2,
    "Admin": 3,
}


SECURITY_LEVEL_ROLES = {
    1: "Lager",
    2: "Management",
    3: "Admin",
}


USERS = {
    "lager_user": {
        "password_hash": "pbkdf2_sha256$260000$df208e55e985c6c9b70f78e3afa4f1b1$44e989860b85dcce2fda2dcbc5d3d9874f6e07111d6214fe0f67086cd0791d6e",
        "role": "Lager",
    },
    "management_user": {
        "password_hash": "pbkdf2_sha256$260000$3efe4885f0ac9032a1dac7dbb3956905$f44ceba7a438572edcb76da1aef1c29bff05f84a200a23d1487179cae85589e6",
        "role": "Management",
    },
    "admin_user": {
        "password_hash": "pbkdf2_sha256$260000$6b9cb3106b5265884990f5d130ca7b63$2c0ad7e577ee4bdbd166a11e596b9f4773461204f60f6e64506cf2db517d1442",
        "role": "Admin",
    },
}


def get_login_roles():
    """
    Liefert nur die Rollen, die im aktuellen Systemkonzept erlaubt sind.
    """

    return list(ROLE_SECURITY_LEVELS.keys())


def get_role_security_level(role):
    return ROLE_SECURITY_LEVELS.get(role, 0)


def get_role_for_security_level(security_level):
    security_level = int(security_level or 0)

    if security_level >= 3:
        return "Admin"

    return SECURITY_LEVEL_ROLES.get(security_level)


def verify_password(password, password_hash):
    """
    Prueft ein PBKDF2-Passwort ohne Klartextpasswoerter im Code zu speichern.
    """

    try:
        method, iterations, salt, expected_hash = password_hash.split("$")
    except ValueError:
        return False

    if method != "pbkdf2_sha256":
        return False

    calculated_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations)
    ).hex()

    return hmac.compare_digest(calculated_hash, expected_hash)


def _authenticate_db_user(username, password):
    if not is_database_configured():
        return None

    row = fetch_one("""
        SELECT
            USERNAME,
            USERPASS,
            SECURITYLEVEL
        FROM dbo.T_USER
        WHERE USERNAME = ?
    """, [username])

    if row is None:
        return None

    db_role = get_role_for_security_level(row.get("SECURITYLEVEL"))

    if db_role is None:
        return None

    if str(row.get("USERPASS") or "") != str(password or ""):
        return None

    return {
        "username": row["USERNAME"],
        "role": db_role,
        "security_level": int(row["SECURITYLEVEL"]),
    }


def authenticate_user(username, password):
    """
    Benutzername und Passwort muessen zusammenpassen.
    Die Berechtigungen ergeben sich anschliessend aus dem Securitylevel.
    """

    username = (username or "").strip()

    try:
        db_user = _authenticate_db_user(username, password)

        if db_user is not None:
            return db_user

    except Exception as exc:
        print("DB-Login konnte nicht verwendet werden:")
        print(exc)

    user = USERS.get(username)

    if user is None:
        return None

    if not verify_password(password or "", user["password_hash"]):
        return None

    security_level = get_role_security_level(user["role"])

    return {
        "username": username,
        "role": get_role_for_security_level(security_level),
        "security_level": security_level,
    }
