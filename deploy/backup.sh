#!/usr/bin/env bash
# ============================================================
# 数据资产管理平台 — 月度数据库备份脚本
# 由 cron 每月 2 号 03:30 自动调用（错开商会 1 号 03:00）
# 保留最近 6 个月的备份，自动清理过期文件
# ============================================================
set -euo pipefail

BACKUP_DIR="/var/backups/data-asset-platform"
KEEP_MONTHS=6
TIMESTAMP=$(date +%Y-%m)
APP_DIR="/opt/data-asset-platform"
ENV_FILE="$APP_DIR/backend/.env"

# ① 检查 .env 是否存在
if [ ! -f "$ENV_FILE" ]; then
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') — .env 不存在，无法读取数据库连接信息"
    exit 1
fi

# ② 从 DATABASE_URL 提取连接信息
# 格式: postgresql://user:password@host:port/dbname
DB_URL=$(grep DATABASE_URL "$ENV_FILE" | cut -d= -f2-)
DB_USER=$(echo "$DB_URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')
DB_PASS=$(echo "$DB_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
DB_HOST=$(echo "$DB_URL" | sed -n 's|.*@\([^:]*\):.*|\1|p')
DB_NAME=$(echo "$DB_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')

if [ -z "$DB_NAME" ]; then
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') — 无法从 DATABASE_URL 解析数据库名"
    exit 1
fi

mkdir -p "$BACKUP_DIR"

BACKUP_FILE="${BACKUP_DIR}/data_assets_backup_${TIMESTAMP}.sql.gz"

# ③ 执行 pg_dump 并压缩
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始备份 $DB_NAME..."

PGPASSWORD="$DB_PASS" pg_dump \
    -h "$DB_HOST" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    | gzip > "$BACKUP_FILE"

# ④ 验证备份文件非空
if [ ! -s "$BACKUP_FILE" ]; then
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') — 备份文件为空！请检查数据库连接"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份完成: $BACKUP_FILE"
echo "  文件大小: $(du -h "$BACKUP_FILE" | cut -f1)"

# ⑤ 清理超过 KEEP_MONTHS 个月的备份
DELETED=$(find "$BACKUP_DIR" -name "data_assets_backup_*.sql.gz" -mtime +$((KEEP_MONTHS * 30)) -delete -print)
if [ -n "$DELETED" ]; then
    echo "  清理过期备份:"
    echo "$DELETED"
fi

echo "  当前保留备份数: $(ls "$BACKUP_DIR" 2>/dev/null | wc -l)"
