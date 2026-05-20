import hashlib
import json
import os
import secrets
import sqlite3
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "gateway_audit.db"
USERS_PATH = BASE_DIR / "users.json"
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RTX_HOST = os.getenv("RTX_HOST", "phh@192.168.120.155")
PROJECT_ROOT = os.getenv("PROJECT_ROOT", "/home/phh/magiclab_rl_lab")
SUBMIT_SCRIPT = os.getenv(
    "SUBMIT_SCRIPT",
    "D:/Desktop_Files/GPU-Train/RTX6000/rtx_submit_orchestrator_train.sh",
)
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-env")
TOKEN_TTL_HOURS = int(os.getenv("TOKEN_TTL_HOURS", "12"))
ALLOWED_IPS = {ip.strip() for ip in os.getenv("ALLOWED_IPS", "").split(",") if ip.strip()}

serializer = URLSafeTimedSerializer(JWT_SECRET)
bearer = HTTPBearer(auto_error=False)
app = FastAPI(title="GPU-Train Gateway", version="1.0.0")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class LoginReq(BaseModel):
    username: str
    password: str


class ActionReq(BaseModel):
    note: Optional[str] = None


class StartFromReq(BaseModel):
    sub_phase: str
    note: Optional[str] = None


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                user TEXT NOT NULL,
                role TEXT NOT NULL,
                action TEXT NOT NULL,
                remote_ip TEXT,
                status TEXT NOT NULL,
                detail TEXT
            )
            """
        )


def load_users() -> Dict[str, Any]:
    if not USERS_PATH.exists():
        raise RuntimeError(f"Missing users file: {USERS_PATH}")
    return json.loads(USERS_PATH.read_text(encoding="utf-8"))


def hash_password(password: str, salt: str) -> str:
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return h.hex()


def check_allowed_ip(request: Request) -> None:
    if not ALLOWED_IPS:
        return
    client_ip = request.client.host if request.client else ""
    if client_ip not in ALLOWED_IPS:
        raise HTTPException(status_code=403, detail="IP not allowed")


def issue_token(username: str, role: str) -> str:
    payload = {
        "u": username,
        "r": role,
        "nonce": secrets.token_hex(8),
        "iat": int(time.time()),
    }
    return serializer.dumps(payload)


def parse_token(token: str) -> Dict[str, Any]:
    try:
        return serializer.loads(token, max_age=TOKEN_TTL_HOURS * 3600)
    except SignatureExpired as e:
        raise HTTPException(status_code=401, detail="Token expired") from e
    except BadSignature as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e


def audit(user: str, role: str, action: str, request: Request, status: str, detail: str = "") -> None:
    ip = request.client.host if request.client else ""
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO audit(ts,user,role,action,remote_ip,status,detail) VALUES(?,?,?,?,?,?,?)",
            (utcnow(), user, role, action, ip, status, detail[:4000]),
        )


def sh(cmd: str, timeout: int = 120) -> str:
    out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT, timeout=timeout)
    return out.strip()


def role_guard(user: Dict[str, Any], need: str) -> None:
    rank = {"viewer": 1, "operator": 2, "admin": 3}
    if rank.get(user["role"], 0) < rank.get(need, 0):
        raise HTTPException(status_code=403, detail=f"Role {need}+ required")


def current_user(
    request: Request,
    cred: HTTPAuthorizationCredentials = Depends(bearer),
) -> Dict[str, Any]:
    check_allowed_ip(request)
    if not cred:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    data = parse_token(cred.credentials)
    return {"username": data["u"], "role": data["r"]}


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "ttl": TOKEN_TTL_HOURS})


@app.post("/api/login")
def login(req: LoginReq, request: Request):
    check_allowed_ip(request)
    users = load_users().get("users", [])
    for u in users:
        if u.get("username") != req.username:
            continue
        hashed = hash_password(req.password, u["salt"])
        if hashed != u["password_hash"]:
            break
        token = issue_token(u["username"], u["role"])
        audit(u["username"], u["role"], "login", request, "ok")
        return {"token": token, "role": u["role"], "expires_hours": TOKEN_TTL_HOURS}
    audit(req.username, "unknown", "login", request, "fail")
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/api/health")
def health(user: Dict[str, Any] = Depends(current_user)):
    return {"ok": True, "user": user["username"], "role": user["role"]}


@app.get("/api/status")
def status(request: Request, user: Dict[str, Any] = Depends(current_user)):
    squeue = sh(f"ssh {RTX_HOST} \"squeue -u {RTX_HOST.split('@')[0]}\"", timeout=60)
    state = sh(
        "ssh "
        + RTX_HOST
        + " \"python3 - <<'PY'\n"
        + "import json, pathlib\n"
        + f"p=pathlib.Path('{PROJECT_ROOT}/orchestrator_state.json')\n"
        + "print('STATE_EXISTS', p.exists())\n"
        + "if p.exists():\n"
        + " s=json.loads(p.read_text(encoding='utf-8'))\n"
        + " for k in ['current_phase_id','current_stage_id','current_stage_status','best_checkpoint_path','best_reward','training_pid','updated_at']:\n"
        + "  print(f'{k}={s.get(k)}')\n"
        + "PY\"",
        timeout=60,
    )
    audit(user["username"], user["role"], "status", request, "ok")
    return {"squeue": squeue, "state": state}


@app.get("/api/tail")
def tail(request: Request, lines: int = 30, user: Dict[str, Any] = Depends(current_user)):
    lines = max(10, min(lines, 200))
    out = sh(
        f"ssh {RTX_HOST} \"tail -{lines} {PROJECT_ROOT}/logs/slurm-z1_orch-73.out 2>/dev/null || true; echo '---'; tail -{lines} {PROJECT_ROOT}/logs/train_p3_coarse.log 2>/dev/null || true\"",
        timeout=60,
    )
    audit(user["username"], user["role"], "tail", request, "ok", f"lines={lines}")
    return {"log": out}


@app.post("/api/orchestrator/resume")
def resume(req: ActionReq, request: Request, user: Dict[str, Any] = Depends(current_user)):
    role_guard(user, "operator")
    cmd = f"& 'C:/Program Files/Git/bin/bash.exe' -lc 'bash {SUBMIT_SCRIPT.replace('D:/', '/d/')} --resume'"
    try:
        out = sh(cmd, timeout=180)
        audit(user["username"], user["role"], "orchestrator_resume", request, "ok", req.note or "")
        return {"output": out}
    except subprocess.CalledProcessError as e:
        audit(user["username"], user["role"], "orchestrator_resume", request, "fail", e.output)
        raise HTTPException(status_code=500, detail=e.output)


@app.post("/api/orchestrator/start-from")
def start_from(req: StartFromReq, request: Request, user: Dict[str, Any] = Depends(current_user)):
    role_guard(user, "operator")
    safe_phase = req.sub_phase.strip()
    if not safe_phase or any(c in safe_phase for c in " ;|&\""):
        raise HTTPException(status_code=400, detail="Invalid sub_phase")
    cmd = f"& 'C:/Program Files/Git/bin/bash.exe' -lc 'bash {SUBMIT_SCRIPT.replace('D:/', '/d/')} --from {safe_phase}'"
    try:
        out = sh(cmd, timeout=180)
        audit(user["username"], user["role"], "orchestrator_start_from", request, "ok", safe_phase)
        return {"output": out}
    except subprocess.CalledProcessError as e:
        audit(user["username"], user["role"], "orchestrator_start_from", request, "fail", e.output)
        raise HTTPException(status_code=500, detail=e.output)


@app.get("/api/audit")
def get_audit(request: Request, limit: int = 100, user: Dict[str, Any] = Depends(current_user)):
    role_guard(user, "admin")
    limit = max(10, min(limit, 500))
    with db_conn() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,))]
    audit(user["username"], user["role"], "audit_read", request, "ok", f"limit={limit}")
    return {"rows": rows}
