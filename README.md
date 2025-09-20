# Flask Blog

一個以 Flask 打造的部落格與簡易 CMS，提供文章管理、分類維護、SEO 友善的公開頁面與安全性最佳化。此專案同時支援開發與生產環境部署流程，並將商業邏輯整理為 Blueprint、Service 與 Form，以便於擴充與維護。

## 功能亮點
- **公開網站**：首頁文章串、分類列表、單篇文章頁、`robots.txt`、`sitemap.xml` 等 SEO 需求皆內建。
- **後台管理介面**：登入驗證、文章 CRUD、草稿 / 發佈流程、分類維護，以及快取清理與統計資訊。
- **安全設計**：CSRF 防護、Content Security Policy（含 nonce）、強制 HTTPS、Bleach HTML 清洗與登入異常記錄。
- **效能與穩定性**：`Flask-Caching` 快取常用查詢、循環檔案日誌與 Syslog 支援、儀表板統計快取化。
- **可維運性**：Flask-Migrate 資料庫遷移、`deploy.sh` 部署腳本、`app_launcher.py` 多環境啟動器，讓部署與設定更一致。

## 技術棧
- Python 3.11+、Flask 3.1、Jinja2
- Flask-SQLAlchemy、Flask-Migrate、Alembic
- Flask-Login、Flask-WTF、WTForms
- Flask-Caching、Bleach、python-dotenv
- Gunicorn、Nginx、systemd（部署腳本示例）

## 專案結構
```text
.
├── app/
│   ├── __init__.py
│   ├── forms.py
│   ├── models.py
│   ├── routes/
│   │   ├── public.py
│   │   └── dashboard.py
│   ├── services/
│   │   ├── category_service.py
│   │   ├── post_service.py
│   │   └── statistics_service.py
│   ├── templates/
│   │   ├── auth/
│   │   ├── blog/
│   │   ├── dashboard/
│   │   ├── error/
│   │   ├── main/
│   │   └── sitemap.xml
│   ├── static/
│   │   ├── css/
│   │   ├── fonts/
│   │   ├── images/
│   │   └── robots.txt
│   └── utils.py
├── app_launcher.py
├── config.py
├── deploy.sh
├── instance/
│   └── blog.db
├── migrations/
│   ├── env.py
│   └── versions/
├── requirements.txt
└── README.md
```

## 系統需求
- Python 3.11 或更新版本
- SQLite（預設）、PostgreSQL 或其他 SQLAlchemy 支援的資料庫
- 推薦使用虛擬環境（`venv` 或 `pyenv`）

## 快速開始
1. 建立並啟用虛擬環境：
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
2. 複製 `.env`（可放在專案根目錄或透過 `ENV_PATH` 指定）：
   ```ini
   FLASK_ENV=development
   SECRET_KEY=please-change-me
   DATABASE_URL=sqlite:///instance/blog.db
   TIMEZONE=Asia/Taipei
   LOG_FILE=logs/app.log
   FORCE_HTTPS=false
   APP_VERSION=1.0.0
   # 可選設定
   # CACHE_TYPE=SimpleCache
   # CACHE_DEFAULT_TIMEOUT=300
   # SITEMAP_STATIC_ROUTES=main.index,main.category
   ```
3. 初始化資料庫（會自動建立 `instance/` 目錄與 sqlite 檔案）：
   ```bash
   flask --app app_launcher db upgrade
   ```
4. 建議先建立管理員帳號：
   ```bash
   flask --app app_launcher shell
   >>> from app import db
   >>> from app.models import User
   >>> admin = User(username="admin", email="admin@example.com", is_admin=True)
   >>> admin.set_password("strong-password")
   >>> db.session.add(admin); db.session.commit()
   ```
5. 啟動開發伺服器：
   ```bash
   python app_launcher.py --dev
   # 或使用 Flask CLI
   flask --app app_launcher run --debug
   ```
6. 造訪網站：
   - 前台首頁：http://localhost:8080/
   - 後台登入：http://localhost:8080/admin_login/
   - 後台儀表板：http://localhost:8080/dashboard/

## 設定與環境變數
`config.py` 定義了 `DevelopmentConfig` 與 `ProductionConfig`：
- `SECRET_KEY`：必填，用於 session 與 CSRF。
- `DATABASE_URL`：SQLAlchemy 連線字串。Development 預設為 `sqlite:///instance/blog.db`。
- `TIMEZONE`：模板顯示時間使用的時區。
- `LOG_FILE`：生產模式的輪替檔案日誌路徑。
- `FORCE_HTTPS`：生產模式預設為 `true`，可在開發時關閉。
- `CACHE_TYPE`、`CACHE_DEFAULT_TIMEOUT`：Flask-Caching 設定。
- `SITEMAP_STATIC_ROUTES`：自訂 Sitemap 靜態頁面端點清單。

可透過下列指令驗證設定是否正確：
```bash
python app_launcher.py --check-config
```

## 主要 Blueprint 與路由
- `main_bp`（`/`）：首頁、分類、單篇文章。
- `auth_bp`：`/admin_login/` 登入、`/logout/` 登出。
- `sitemap_bp`：`/sitemap.xml` 自動輸出發佈文章並支援動態 `changefreq`/`priority`。
- `dashboard`（`/dashboard`）：文章列表、預覽、草稿/發佈、分類 CRUD。

## 資料庫與遷移
- 使用 Flask-Migrate / Alembic。首次使用請執行 `flask --app app_launcher db upgrade`。
- 若需新增資料表或欄位：
  ```bash
  flask --app app_launcher db migrate -m "Add something"
  flask --app app_launcher db upgrade
  ```
- `app/services/category_service.py` 會在建立文章時確保 `Uncategorized` 預設分類存在。

## 安全與最佳實務
- **CSRF**：預設開啟，若表單模板需判斷可使用 `csrf_enabled` 變數。
- **CSP**：自動為 `script-src` / `style-src` 加上 runtime nonce，並可依環境調整白名單。
- **HTML 清洗**：`app.utils.clean_html_content` 使用 Bleach 白名單，避免惡意 XSS。
- **強制 HTTPS**：生產環境預設會 301 Redirect 至 HTTPS 並設定 HSTS。
- **登入安全**：失敗登入會記錄日誌，`LoginManager` 使用電子郵件查詢帳號。

## 快取與效能
- `Flask-Caching` 以 `SimpleCache` 為預設，可透過 `.env` 切換至 Redis/Memcached。
- 文章與分類的表單選單、導覽列、儀表板統計皆使用快取並在 CRUD 後清除。
- `StatisticsService` 與 `CategoryService` 提供快取清除方法，可於自訂腳本中復用。

## 日誌與監控
- 開發模式：使用 `StreamHandler`，輸出至終端機。
- 生產模式：`RotatingFileHandler`，亦嘗試註冊 `/dev/log` Syslog handler。
- 可依需求整合外部監控，預設提供輪替檔案日誌與 Syslog 介接。

## 部署指引
1. 確保系統已安裝 Git、Python、virtualenv、systemd、Nginx。
2. 伺服器上執行 `deploy.sh` 會自動完成：
   - `git pull`
   - 啟用 `venv`
   - `pip install -r requirements.txt`
   - `flask db upgrade`
   - 重新啟動 `flask-blog` systemd 與 Nginx
3. WSGI 執行範例：
   ```bash
   gunicorn -w 4 app_launcher:app
   ```
4. 使用自訂環境變數覆寫 `ProductionConfig`，部署前可先執行 `python app_launcher.py --check-config`。

## 測試與品質
- 建議使用 `pytest` 或 `unittest` 編寫測試，可依需求撰寫資料庫與路由測試案例。
- 上線前請逐一驗證主要流程（登入、發佈文章、產生 Sitemap）。

## 常見問題
- **登入後仍回到登入頁**：確認 `SECRET_KEY` 在重啟後保持一致，或清除瀏覽器 Cookie。
- **Sitemap 少了特定頁面**：確認文章 `status` 是否為 `published`，或在 `.env` 設定 `SITEMAP_STATIC_ROUTES`。
- **無法寫入日誌**：檢查 `LOG_FILE` 目錄權限，或在 `.env` 將路徑改至可寫入的位置。
- **部署時強制 HTTPS 造成迴圈**：在反向代理（如 Nginx）設定 `X-Forwarded-Proto https` header，或暫時將 `FORCE_HTTPS=false` 以排除原因。

## 授權
專案維持私有或依原作者需求決定。若需開源，建議新增授權條款（例如 MIT、Apache 2.0 等）。
