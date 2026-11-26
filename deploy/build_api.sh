#!/usr/bin/env bash
# 組出 Vercel 後端部署資料夾：.tmp/deploy-api（保持 apps/api/app 與 data/ 的相對位置，引擎才找得到法規與規則）
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=.tmp/deploy-api
rm -rf "$OUT" && mkdir -p "$OUT/api" "$OUT/apps/api" "$OUT/data"
rsync -a --exclude '__pycache__' apps/api/app "$OUT/apps/api/"
rsync -a data/legal data/rules data/evaluation data/i18n "$OUT/data/"
cp deploy/api_index.py "$OUT/api/index.py"
cp deploy/requirements.prod.txt "$OUT/requirements.txt"
cp deploy/vercel.api.json "$OUT/vercel.json"
echo "$OUT"
