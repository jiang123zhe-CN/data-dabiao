#!/usr/bin/env bash
# ============================================================
# 数据资产管理平台 — 阿里云 2C2G 一键部署脚本
# 与商会资源撮合平台（chamber-platform）共存于同一台服务器
#
# 用法：ssh 到服务器后，以 root 执行 bash deploy.sh
# 前提：代码已放在 /opt/data-asset-platform（git clone 或 scp）
#
# 端口分配：
#   商会平台  — Nginx :80 → /api/*  → 127.0.0.1:8000
#   数据资产  — Nginx :80 → /dam/* → 127.0.0.1:8001
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
log()   { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

APP_DIR="/opt/data-asset-platform"
APP_PORT=8001                                    # ① 避开商会的 8000 端口
APP_PATH="/dam"                                   # ② URL 子路径前缀
DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-your-dashscope-api-key}"
APP_ENV="${APP_ENV:-production}"

# ---- 0. 基础检查 ----
if [ "$(id -u)" -ne 0 ]; then
    error "请用 root 执行此脚本"
    exit 1
fi

if [ ! -d "$APP_DIR/backend" ]; then
    error "代码目录 $APP_DIR 不存在，请先 git clone 或 scp 上传代码到此路径"
    exit 1
fi

log "开始部署数据资产管理平台..."
log "URL 路径前缀: ${APP_PATH}  |  API 端口: ${APP_PORT}"

# ---- 1. 系统依赖（跳过已在商会部署中安装的包）----
log "检查系统依赖..."
apt-get update -qq

# ① 仅安装缺失的包，避免重复安装浪费时间
MISSING=""
for pkg in python3 python3-pip python3-venv postgresql nginx curl; do
    dpkg -s "$pkg" &>/dev/null || MISSING="$MISSING $pkg"
done
if [ -n "$MISSING" ]; then
    log "安装缺失的系统包:$MISSING"
    apt-get install -y -qq $MISSING
else
    log "系统依赖已就绪，跳过"
fi

# ② Node.js — 如果未安装则安装 18.x
if ! command -v node &>/dev/null; then
    log "安装 Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y -qq nodejs
else
    log "Node.js $(node -v) 已安装"
fi

# ---- 2. 确保 swap 存在（内存安全垫）----
if ! swapon --show | grep -q swap; then
    log "创建 2GB swap 文件..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    warn "swap 已创建 — 2GB 内存紧张时可应急"
else
    log "swap 已存在，跳过"
fi

# ---- 3. PostgreSQL 配置（复用已有 PG 实例，仅建库）----
log "配置 PostgreSQL 数据库..."

# ③ 确保 PG 正在运行
systemctl is-active --quiet postgresql || systemctl start postgresql
systemctl enable postgresql

# ④ 检查 chamber_user 是否存在（由商会部署脚本创建）
CHAMBER_USER_EXISTS=$(sudo -u postgres psql -tAc \
    "SELECT 1 FROM pg_roles WHERE rolname='chamber_user'" 2>/dev/null || echo "0")

if [ "$CHAMBER_USER_EXISTS" = "1" ]; then
    log "复用已有数据库用户 chamber_user"
    DB_USER="chamber_user"
    # ⑤ 从商会 .env 读取已有密码，确保一致性
    CHAMBER_ENV="/opt/chamber-platform/backend/.env"
    if [ -f "$CHAMBER_ENV" ]; then
        DB_PASSWORD=$(grep DATABASE_URL "$CHAMBER_ENV" | \
            sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
        log "从商会配置中读取到数据库密码"
    else
        error "商会 .env 不存在，无法获取数据库密码"
        error "请先部署商会平台，或手动设置 DB_PASSWORD 环境变量"
        exit 1
    fi
else
    warn "chamber_user 不存在，创建新用户..."
    DB_USER="dam_user"
    DB_PASSWORD=$(openssl rand -base64 16 | tr -d '/+=' | cut -c1-16)
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
fi

# ⑥ 创建数据资产管理数据库
sudo -u postgres psql -c "CREATE DATABASE data_assets OWNER $DB_USER;" 2>/dev/null || \
    warn "数据库 data_assets 已存在，跳过创建"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE data_assets TO $DB_USER;"

DB_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:5432/data_assets"
log "数据库连接: postgresql://${DB_USER}:****@localhost:5432/data_assets"

# ---- 4. 后端部署 ----
log "部署后端..."
cd "$APP_DIR/backend"

# ⑦ Python 虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# ⑧ 生成安全密钥
SECRET_KEY=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(openssl rand -base64 32)

# ⑨ 写入 .env（覆盖开发配置）
cat > .env <<EOF
# === 应用 ===
APP_NAME=数据资产管理平台
APP_VERSION=1.0.0
DEBUG=false

# === 数据库（PostgreSQL — 与商会平台共用实例）===
DATABASE_URL=${DB_URL}

# === JWT 认证 ===
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# === 阿里云 DashScope（通义千问）===
DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}

# === 加密密钥 ===
ENCRYPTION_KEY=${ENCRYPTION_KEY}
EOF
chown root:www-data .env
chmod 640 .env
log ".env 已生成"

# ⑩ 初始化数据库表 + 种子数据
log "初始化数据库..."
python seed.py
log "数据库表已创建，种子数据已写入"

# ---- 5. 前端构建 ----
log "构建前端（路径前缀: ${APP_PATH}）..."
cd "$APP_DIR/frontend"

# ⑪ 备份需要临时修改的源文件
cp src/main.jsx src/main.jsx.bak
cp src/services/api.js src/services/api.js.bak

# ⑫ 临时修改：BrowserRouter basename → 子路径
sed -i "s|<BrowserRouter>|<BrowserRouter basename=\"${APP_PATH}\">|" src/main.jsx

# ⑬ 临时修改：API baseURL → 子路径前缀
sed -i "s|baseURL: '/api'|baseURL: '${APP_PATH}/api'|" src/services/api.js

# ⑭ 执行构建（限制 Node 堆大小适配 2GB 内存）
export NODE_OPTIONS="--max-old-space-size=512"
npm install --silent
npx vite build --base="${APP_PATH}/"

# ⑮ 恢复源文件
mv src/main.jsx.bak src/main.jsx
mv src/services/api.js.bak src/services/api.js
log "源文件已恢复"

# ⑯ 部署静态文件到 Nginx 目录（先清空避免旧版本残留）
rm -rf /var/www${APP_PATH}/*
mkdir -p /var/www${APP_PATH}
cp -r dist/* /var/www${APP_PATH}/
chown -R www-data:www-data /var/www${APP_PATH}
log "静态文件已部署到 /var/www${APP_PATH}/"

# ---- 6. Nginx 配置（与商会平台合并到同一 server block）----
log "配置 Nginx（合并商会 + 数据资产路由）..."

NGX_CONF="/etc/nginx/sites-available/chamber-platform"
NGX_DAM_MARKER="# === 数据资产管理平台（由 dam deploy.sh 自动添加）==="

# ⑰ 检查是否已配置过 dam 路由
if [ -f "$NGX_CONF" ] && grep -q "$NGX_DAM_MARKER" "$NGX_CONF"; then
    log "Nginx 已包含数据资产管理平台路由，跳过合并"
else
    if [ -f "$NGX_CONF" ]; then
        # ⑱ 商会配置已存在 → 在 SPA fallback 前插入 dam 路由
        log "检测到商会 Nginx 配置，插入数据资产管理平台路由..."

        # 找到 "# ④ SPA fallback" 注释行，在其前插入 dam 配置
        DAM_NGINX_BLOCK=$(cat <<'NGXDAM'

	# === 数据资产管理平台（由 dam deploy.sh 自动添加）===
	# ① 数据资产 API 反向代理 → 127.0.0.1:8001
	location /dam/api/ {
	    rewrite ^/dam(.*) $1 break;
	    proxy_pass http://127.0.0.1:8001;
	    proxy_set_header Host $host;
	    proxy_set_header X-Real-IP $remote_addr;
	    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
	    proxy_set_header X-Forwarded-Proto $scheme;
	    proxy_read_timeout 120s;
            proxy_redirect ~^http://[^/]*/(.*)$ /dam/$1;
	}

	# ② 数据资产前端静态文件
	location /dam/ {
	    root /var/www;
	    index index.html;
	    try_files $uri $uri/ /dam/index.html;
	}
NGXDAM
)
        # 使用 awk 在 SPA fallback 的 "location / {" 之前插入
        # 匹配行首带空格的 "location / {"（不是 /api/ 或 /assets/ 等）
        awk -v block="$DAM_NGINX_BLOCK" '
            /^[[:space:]]+location \/ \{/ { print block }
            { print }
        ' "$NGX_CONF" > "${NGX_CONF}.tmp" && mv "${NGX_CONF}.tmp" "$NGX_CONF"

        log "Nginx 配置已合并"
    else
        # ⑲ 商会配置不存在 → 创建仅包含数据资产平台的独立配置
        warn "未找到商会 Nginx 配置，创建独立配置..."
        cat > "$NGX_CONF" <<NGXEOF
server {
    listen 80;
    server_name _;

    ${NGX_DAM_MARKER}
    # ① 数据资产 API 反向代理 → 127.0.0.1:8001
    location /dam/api/ {
        rewrite ^/dam(.*) \$1 break;
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
            proxy_redirect ~^http://[^/]*/(.*)$ /dam/$1;
    }

    # ② 数据资产前端静态文件
    location /dam/ {
        root /var/www;
        index index.html;
        try_files \$uri \$uri/ /dam/index.html;
    }

    # ③ 默认首页跳转到数据资产平台
    location = / {
        return 302 /dam/;
    }
}
NGXEOF
    fi
fi

# ⑳ 启用配置并重载
ln -sf "$NGX_CONF" /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
systemctl enable nginx
log "Nginx 已重载"

# ---- 7. Systemd 服务 ----
log "配置后端服务（端口 ${APP_PORT}）..."
cat > /etc/systemd/system/dam-api.service <<SVCSEOF
[Unit]
Description=Data Asset Management Platform API
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=${APP_DIR}/backend
Environment=PATH=${APP_DIR}/backend/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=${APP_DIR}/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${APP_PORT} --workers 1
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCSEOF

systemctl daemon-reload
systemctl enable dam-api
systemctl restart dam-api  # restart 兼顾首次启动和重新部署
log "dam-api.service 已启动"

# ---- 8. 月度备份 ----
log "配置月度备份..."
cp "$APP_DIR/deploy/backup.sh" /usr/local/bin/dam-backup
chmod +x /usr/local/bin/dam-backup
# 每月 2 号凌晨 03:30 执行（错开商会的 1 号 03:00，避免同时 pg_dump 打满 IO）
(crontab -l 2>/dev/null | grep -v "dam-backup"; echo "30 3 2 * * /usr/local/bin/dam-backup >> /var/log/dam-backup.log 2>&1") | crontab -
warn "月度备份已配置（每月 2 号 03:30）"

# ---- 9. 部署结果 ----
echo ""
echo "============================================"
echo -e "${GREEN}  数据资产管理平台 — 部署完成！${NC}"
echo "============================================"
echo ""
echo "  前端页面:    http://服务器IP/dam/"
echo "  后端 API:    http://服务器IP/dam/api/health"
echo "  后端状态:    systemctl status dam-api"
echo "  后端日志:    journalctl -u dam-api -f"
echo ""
echo "  ⚠️  请确保阿里云安全组已开放 80 端口（TCP）"
echo "  ⚠️  后端端口 ${APP_PORT} 仅监听 127.0.0.1，不对外暴露"
echo ""
echo "  数据库:      postgresql://${DB_USER}:****@localhost:5432/data_assets"
echo "  .env 位置:   ${APP_DIR}/backend/.env"
echo ""
echo "  备份配置:     每月 2 号 03:30 自动备份"
echo "  备份位置:     /var/backups/data-asset-platform/"
echo "  手动备份:     dam-backup"
echo ""
echo "  默认管理员:   admin / admin123"
echo "  （请在生产环境立即修改密码）"
echo ""
echo "  与商会平台共存:"
echo "    商会平台 — http://服务器IP/"
echo "    数据资产 — http://服务器IP/dam/"
echo "============================================"
