#!/bin/bash
# 部署腳本 - 在Droplet上運行

set -e

echo "🚀 開始部署Flask Blog..."

# 拉取最新代碼
echo "📥 拉取最新代碼..."
git pull origin main

# 激活虛擬環境
echo "🐍 激活Python環境..."
source venv/bin/activate

# 安裝/更新依賴
echo "📦 安裝依賴..."
pip install -r requirements.txt

# 運行資料庫遷移
echo "🗄️ 運行資料庫遷移..."
flask db upgrade

# 重啟Gunicorn服務
echo "🔄 重啟應用服務..."
sudo systemctl restart flask-blog

# 重載Nginx
echo "🌐 重載Nginx..."
sudo systemctl reload nginx

# 檢查服務狀態
echo "✅ 檢查服務狀態..."
sudo systemctl status flask-blog --no-pager -l
sudo systemctl status nginx --no-pager -l

echo "🎉 部署完成！"
echo "💡 檢查網站：curl -I http://$(curl -s ifconfig.me)"