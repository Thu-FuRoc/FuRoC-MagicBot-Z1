# GPU-Train Gateway (Stable Architecture)

This gateway lets remote teammates monitor and operate training **without getting VPN/SSH credentials**.

## What it provides

- Login + role-based access (`viewer` / `operator` / `admin`)
- Read-only APIs: status, log tail
- Controlled actions: orchestrator resume, start-from
- Audit logs in SQLite (`data/gateway_audit.db`)

## Files

- `gateway_server.py`: FastAPI gateway
- `templates/index.html`: built-in web console
- `users.json`: local user database (hashed passwords)
- `start_gateway.bat`: run service
- `open_dashboard.bat`: open browser

## First run

1. Edit `start_gateway.bat`:
- Set `JWT_SECRET` to a long random string
- Optionally set `ALLOWED_IPS=ip1,ip2`

2. Start service:

```bat
start_gateway.bat
```

3. Open dashboard:

```bat
open_dashboard.bat
```

Default user from `init_users.py`:
- username: `admin`
- password: `ChangeMe!123`

Change password immediately by regenerating `users.json`.

## Remote access (stable recommendation)

Put this service behind one of:

1. **Tailscale** (recommended fast setup)
2. **Cloudflare Tunnel + Access**
3. **Public IP + Caddy/Nginx + TLS + IP whitelist**

Do NOT expose SSH/VPN credentials. Teammates only call this gateway.

## Security notes

- Keep iNode VPN and this gateway running on the middle machine
- Do not share `users.json`
- Rotate `JWT_SECRET` periodically
- Restrict IPs when possible
- Review audit table regularly
