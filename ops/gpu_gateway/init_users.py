import json
import secrets
import hashlib
from pathlib import Path

username = "admin"
password = "ChangeMe!123"
salt = secrets.token_hex(16)
hash_hex = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
obj = {
  "users": [
    {
      "username": username,
      "role": "admin",
      "salt": salt,
      "password_hash": hash_hex,
      "must_change": True
    }
  ]
}
out = Path(__file__).resolve().parent / "users.json"
out.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
print(str(out))
print("default_username=admin")
print("default_password=ChangeMe!123")
