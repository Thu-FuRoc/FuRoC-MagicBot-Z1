# 固定地址配置说明（Cloudflare Named Tunnel）

## 目标

把临时 `*.trycloudflare.com` 改为固定地址（例如 `https://gpu-gateway.yourdomain.com`）。

## 你需要准备（必须）

1. 一个在 Cloudflare 托管的域名（可子域名）
2. Cloudflare Tunnel Token（Named Tunnel）
3. 在 Cloudflare 控制台把该 Tunnel 的 Public Hostname 指向你的子域名

## 本目录文件

- `fixed_tunnel.env`：填入 token 和固定域名
- `start_gateway_local.bat`：启动本地网关（127.0.0.1:8088）
- `start_fixed_tunnel.bat`：启动固定域名隧道

## 使用步骤

1. 编辑 `fixed_tunnel.env`：
   - `TUNNEL_TOKEN=...`
   - `PUBLIC_HOSTNAME=gpu-gateway.yourdomain.com`
2. 运行 `start_gateway_local.bat`
3. 运行 `start_fixed_tunnel.bat`
4. 浏览器打开 `https://PUBLIC_HOSTNAME`

## 给同事发什么

- 固定 HTTPS 地址
- 同事账号密码
- `share_with_teammates/open_gateway.bat`（可改为固定地址）

## 安全建议

- 生产环境务必更换 `JWT_SECRET`
- 限制 `ALLOWED_IPS` 或加 Cloudflare Access
- 默认 admin 密码必须修改
