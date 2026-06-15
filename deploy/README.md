# 数据资产管理平台 — 部署说明

## 服务器要求

- 阿里云轻量应用服务器（2 vCPU / 2 GB RAM / 40 GB 磁盘）
- Ubuntu 22.04 LTS
- 端口 80 已在安全组开放

## 与商会平台的共存关系

| | 商会资源撮合平台 | 数据资产管理平台 |
|---|---|---|
| **Nginx 路径** | `/` | `/dam/` |
| **API 路径** | `/api/*` → 8000 | `/dam/api/*` → 8001 |
| **后端端口** | 8000 | 8001 |
| **数据库** | `chamber_platform` | `data_assets` |
| **数据库用户** | `chamber_user` | 复用 `chamber_user` |
| **Systemd 服务** | `chamber-api` | `dam-api` |
| **备份时间** | 每月 1 号 03:00 | 每月 2 号 03:30 |

两个平台共享同一个 PostgreSQL 实例和 Nginx（同一个 server block），通过不同的 URL 路径前缀区分。

## 一键部署

```bash
# 1. SSH 到服务器
ssh root@8.130.125.243

# 2. 上传代码（首次）或在服务器上 git clone
#    scp -r data-asset-management-platform root@8.130.125.243:/opt/data-asset-platform
#    或
#    cd /opt && git clone <repo-url> data-asset-platform

# 3. 设置 DashScope API Key（部署前）
export DASHSCOPE_API_KEY="sk-your-key-here"

# 4. 执行部署脚本
cd /opt/data-asset-platform/deploy
chmod +x deploy.sh backup.sh
bash deploy.sh
```

## 部署后验证

```bash
# 检查后端服务状态
systemctl status dam-api

# 查看后端日志
journalctl -u dam-api -f

# 检查 API 健康状态
curl http://127.0.0.1:8001/api/health

# 通过 Nginx 访问
curl http://localhost/dam/api/health

# 检查 Nginx 配置
nginx -t
```

## 手动备份

```bash
dam-backup
```

备份文件存储在 `/var/backups/data-asset-platform/`，保留 6 个月。

## 默认账号

| 角色 | 用户名 | 密码 |
|---|---|---|
| 系统管理员 | admin | admin123 |
| 录入员 | data_entry | admin123 |
| 数据管理员 | data_admin | admin123 |
| 复核员 | reviewer | admin123 |

⚠️ 生产环境请立即修改默认密码。

## 端口规划

```
Nginx (:80)
├── /                    → 商会平台前端（SPA）
├── /api/*               → 商会 API → 127.0.0.1:8000
├── /uploads/*           → 商会上传文件
├── /dam/                → 数据资产平台前端（SPA）
└── /dam/api/*           → 数据资产 API → 127.0.0.1:8001

PostgreSQL 14 (:5432)
├── chamber_platform     → 商会数据库
└── data_assets          → 数据资产数据库
```
