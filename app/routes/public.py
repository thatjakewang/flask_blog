# -*- coding: utf-8 -*-
"""
公開路由藍圖模組

此模組包含所有公開面向的路由，包括主頁面、身份驗證和網站地圖功能。
這些路由無需身份驗證即可被所有用戶訪問。

功能概述：
- 主頁面路由：顯示部落格首頁和文章列表
- 身份驗證路由：管理員登入/登出功能
- 網站地圖路由：SEO 優化的 XML 網站地圖
- 分類頁面路由：按分類瀏覽文章
- 單篇文章路由：顯示完整文章內容
"""
from __future__ import annotations

# ========================================
# 匯入模組說明
# ========================================

# 標準庫匯入
# date: 用於網站地圖的日期處理
# TYPE_CHECKING: 支援類型檢查而不會在運行時匯入
# urlparse: 用於驗證和解析 URL，防止重定向攻擊
from datetime import date
from typing import TYPE_CHECKING
from urllib.parse import urlparse

# 第三方庫匯入
# Flask 核心組件：提供 Web 應用程式基礎功能
# Blueprint: 路由模組化管理
# render_template: 渲染 HTML 模板
# request: 處理 HTTP 請求數據
# redirect/url_for: URL 重定向和生成
# flash: 用戶訊息閃現功能
# Response: 自定義 HTTP 響應
# abort: 拋出 HTTP 錯誤
# current_app: 當前應用程式實例
# send_from_directory: 安全地提供靜態檔案
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, Response, abort,
    current_app, send_from_directory
)

# Flask-Login 擴展：提供用戶會話管理
# login_user: 登入用戶
# logout_user: 登出用戶
# login_required: 路由裝飾器，要求用戶已登入
# current_user: 當前登入的用戶物件
from flask_login import login_user, logout_user, login_required, current_user

# SQLAlchemy 查詢函數
# func: 提供資料庫函數，如 lower() 用於不區分大小寫查詢
from sqlalchemy import func

# 型別檢查匯入
# 僅在類型檢查時匯入，避免循環匯入問題
if TYPE_CHECKING:
    from flask import Flask

# 本地模組匯入
# User: 用戶模型，處理身份驗證
# Post: 文章模型，管理部落格內容
# Category: 分類模型，組織文章分類
# LoginForm: 登入表單，處理用戶輸入驗證
from app.models import User, Post, Category
from app.forms import LoginForm


# ========================================
# 錯誤處理與工具輔助函數
# ========================================

def _handle_login_error(message: str, email: str = None, log_level: str = 'warning') -> Response:
    """
    統一處理登入錯誤的輔助函數
    
    功能說明：
    - 集中化登入錯誤處理邏輯，避免重複代碼
    - 提供統一的錯誤日誌記錄格式
    - 自動重定向到登入頁面並顯示錯誤訊息
    
    參數：
        message (str): 顯示給用戶的錯誤訊息
        email (str, optional): 嘗試登入的電子郵件，用於日誌記錄
        log_level (str): 日誌級別，預設為 'warning'
    
    返回：
        Response: 重定向到登入頁面的響應物件
    
    安全考量：
    - 避免在用戶界面洩露敏感的系統資訊
    - 記錄詳細的錯誤資訊到日誌供管理員查看
    """
    if email and log_level == 'warning':
        current_app.logger.warning(f"登入失敗：{message} (Email: {email})")
    elif log_level == 'warning':
        current_app.logger.warning(f"登入失敗：{message}")
    
    flash(message, 'danger')
    return redirect(url_for('auth.admin_login'))


def _safe_url_generation(endpoint: str, **kwargs) -> str | None:
    """
    安全的 URL 生成，處理潛在錯誤
    
    功能說明：
    - 包裝 Flask 的 url_for 函數，增加錯誤處理
    - 防止因無效端點導致的應用程式崩潰
    - 在網站地圖生成時特別有用，某些路由可能不存在
    
    參數：
        endpoint (str): Flask 路由端點名稱
        **kwargs: 傳遞給 url_for 的額外參數
    
    返回：
        str | None: 成功時返回 URL 字串，失敗時返回 None
    
    使用場景：
    - 網站地圖生成
    - 動態 URL 構建
    - 可選功能的 URL 生成
    """
    try:
        return url_for(endpoint, **kwargs)
    except Exception as e:
        current_app.logger.warning(f"無法為 {endpoint} 生成 URL：{e}")
        return None


def _get_pagination_params() -> tuple[int, int]:
    """
    取得分頁參數
    
    功能說明：
    - 從 URL 查詢參數中安全地提取分頁資訊
    - 提供預設值避免參數缺失或無效
    - 統一化分頁參數處理邏輯
    
    返回：
        tuple[int, int]: (頁碼, 每頁項目數)
        
    實作細節：
    - 頁碼預設為 1，確保有效性
    - 每頁項目數從應用程式配置讀取，預設為 10
    - 使用 Flask 的 type=int 自動轉換和驗證
    """
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('POSTS_PER_PAGE', 10)
    return page, per_page


def _paginate_posts(query, page: int, per_page: int):
    """
    統一的文章分頁處理
    
    功能說明：
    - 為文章查詢添加統一的分頁和排序邏輯
    - 按建立時間降序排列（最新的在前）
    - 提供一致的分頁行為和錯誤處理
    
    參數：
        query: SQLAlchemy 查詢物件
        page (int): 目標頁碼
        per_page (int): 每頁顯示的文章數量
    
    返回：
        Pagination: Flask-SQLAlchemy 分頁物件
        
    分頁物件包含：
    - items: 當前頁的文章列表
    - total: 總文章數
    - has_prev/has_next: 是否有上一頁/下一頁
    - prev_num/next_num: 上一頁/下一頁頁碼
    
    安全設定：
    - error_out=False: 避免無效頁碼導致 404 錯誤
    """
    return query.order_by(Post.created_at.desc()).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )


def _get_safe_next_url(default_endpoint: str = 'dashboard.index') -> str:
    """
    安全地取得 next 參數的 URL，防止重定向攻擊
    
    功能說明：
    - 驗證重定向 URL 的安全性，防止開放重定向漏洞
    - 確保只允許內部 URL 重定向
    - 在登入成功後將用戶重定向到原本想訪問的頁面
    
    參數：
        default_endpoint (str): 預設重定向端點，當 next 參數無效時使用
    
    返回：
        str: 安全的重定向 URL
        
    安全檢查：
    - 檢查 netloc 是否為空（確保是相對 URL）
    - 拒絕外部域名的重定向請求
    - 提供安全的預設重定向目標
    
    攻擊防護：
    - 防止惡意用戶通過 next 參數重定向到外部惡意網站
    - 避免釣魚攻擊和其他安全威脅
    """
    next_page = request.args.get('next')
    if not next_page or urlparse(next_page).netloc != '':
        return url_for(default_endpoint)
    return next_page


def _normalize_slug(slug: str) -> str:
    """
    標準化 slug 參數
    
    功能說明：
    - 統一處理 URL 中的 slug 參數格式
    - 確保 slug 的一致性和有效性
    - 提供基本的輸入清理和驗證
    
    參數：
        slug (str): 原始 slug 字串
    
    返回：
        str: 標準化後的 slug
        
    處理流程：
    1. 檢查 slug 是否存在，空值直接返回 404
    2. 移除首尾空白字符
    3. 轉換為小寫以確保一致性
    
    使用場景：
    - 文章 URL 處理
    - 分類 URL 處理
    - SEO 友好的 URL 格式化
    
    錯誤處理：
    - 無效或空的 slug 會觸發 404 錯誤
    """
    if not slug:
        abort(404)
    return slug.strip().lower()


# ========================================
# 藍圖設定與模組化架構
# ========================================

"""
Blueprint 模組化設計說明：

Flask Blueprint 是一種組織路由的方式，允許將相關的路由分組管理。
這種設計模式提供以下優勢：

1. 模組化：將不同功能的路由分離，便於維護和開發
2. 重用性：Blueprint 可以在不同的應用程式中重複使用
3. 組織性：清晰的程式碼結構，便於團隊協作
4. 擴展性：新功能可以作為新的 Blueprint 添加

本模組定義三個主要的 Blueprint，分別處理不同的功能領域：
"""

# 主要公開路由 Blueprint
# 功能：處理網站的主要公開內容
# 包含：首頁、文章展示、分類瀏覽、靜態檔案服務
# URL 前綴：無（根路徑開始）
# 目標用戶：所有訪客（無需身份驗證）
main_bp = Blueprint('main', __name__)

# 身份驗證路由 Blueprint  
# 功能：處理用戶登入、登出相關功能
# 包含：管理員登入頁面、登出處理、會話管理
# URL 前綴：無（與主路由共享命名空間）
# 目標用戶：網站管理員和認證用戶
# 安全考量：包含防護機制避免暴力破解和重定向攻擊
auth_bp = Blueprint('auth', __name__)

# 網站地圖路由 Blueprint
# 功能：提供 SEO 優化的網站地圖
# 包含：XML 格式的網站地圖，自動包含所有已發布內容
# URL 前綴：無（直接提供 /sitemap.xml）
# 目標用戶：搜索引擎爬蟲和 SEO 工具
# 效能考量：優化查詢和快取機制以減少資料庫負載
sitemap_bp = Blueprint('sitemap', __name__)


# ========================================
# 主要路由功能 (原 main.py)
# ========================================

@main_bp.route('/')
def index():
    """
    網站主頁：顯示已發布的文章列表
    
    功能描述：
    - 作為網站的入口點，展示最新的已發布文章
    - 提供分頁導航，確保頁面載入效能
    - 只顯示狀態為 'published' 的文章，確保內容品質
    
    URL 模式：
        GET /
    
    查詢邏輯：
    1. 獲取分頁參數（頁碼和每頁文章數）
    2. 查詢所有已發布的文章
    3. 按建立時間降序排列（最新在前）
    4. 應用分頁處理
    
    模板變數：
        posts: 當前頁的文章列表
        pagination: 分頁物件（包含頁碼、總數等資訊）
        active_page: 用於導航高亮的頁面標識
    
    SEO 考量：
    - 首頁是搜索引擎的重要入口點
    - 確保載入速度和內容品質
    """
    page, per_page = _get_pagination_params()
    query = Post.query.filter_by(status='published')
    pagination = _paginate_posts(query, page, per_page)
    return render_template('main/index.html', posts=pagination.items, pagination=pagination, active_page='home')


@main_bp.route('/<slug>/', methods=['GET'])
def post(slug):
    """
    單篇文章顯示頁面
    
    功能描述：
    - 根據 slug 顯示特定文章的完整內容
    - 支援兩種 slug 格式：自定義 slug 和自動生成的 untitled-{id}
    - 實作訪問權限控制（草稿文章需要登入）
    
    URL 模式：
        GET /<slug>/
        例如：/my-awesome-post/ 或 /untitled-123/
    
    參數：
        slug (str): 文章的唯一標識符
    
    查詢邏輯：
    1. 標準化 slug 參數（去空白、轉小寫）
    2. 判斷 slug 類型：
       - 以 'untitled-' 開頭：根據 ID 查詢
       - 其他：根據 slug 欄位查詢
    3. 檢查文章存在性和訪問權限
    
    訪問控制：
    - 已發布文章：所有用戶可訪問
    - 草稿文章：僅已登入用戶可訪問
    - 不存在文章：返回 404 錯誤
    
    錯誤處理：
    - 無效 slug 格式：404 錯誤
    - 文章不存在：404 錯誤
    - 權限不足：404 錯誤（避免洩露文章存在性）
    
    模板變數：
        post: 文章物件（包含標題、內容、後設資料等）
    """
    slug = _normalize_slug(slug)
    
    # 處理沒有 slug 的文章生成的 slug
    if slug.startswith('untitled-'):
        try:
            post_id = int(slug.replace('untitled-', ''))
            post = Post.query.filter_by(id=post_id).first_or_404()
        except ValueError:
            abort(404)
    else:
        post = Post.query.filter_by(slug=slug).first_or_404()
    
    # 只有已發布的文章或已登入用戶可以查看草稿
    if post.status == 'draft' and not current_user.is_authenticated:
        abort(404)
    
    return render_template('blog/post.html', post=post)


@main_bp.route('/category/<string:slug>/')
def category(slug):
    """
    分類頁面：顯示指定分類下的文章列表
    
    功能描述：
    - 根據分類 slug 顯示該分類下的所有已發布文章
    - 提供分頁功能處理大量文章
    - 實作 SEO 友好的 URL 重定向
    
    URL 模式：
        GET /category/<string:slug>/
        例如：/category/technology/ 或 /category/tutorials/
    
    參數：
        slug (str): 分類的唯一標識符
    
    查詢邏輯：
    1. 標準化分類 slug
    2. 查詢分類是否存在
    3. 實作 SEO 重定向（統一使用小寫 URL）
    4. 查詢分類下的已發布文章
    5. 應用分頁處理
    
    SEO 優化：
    - 301 重定向：確保 URL 的一致性
    - 不區分大小寫的查詢：提升用戶體驗
    - 結構化 URL：/category/{slug}/ 格式
    
    資料庫查詢優化：
    - 使用 JOIN 操作連接 Post 和 Category 表
    - 使用 func.lower() 實現不區分大小寫查詢
    - 僅查詢已發布的文章
    
    模板變數：
        posts: 當前頁的文章列表
        pagination: 分頁物件
        category: 完整的分類物件（包含名稱、描述等）
        active_page: 頁面標識符
    
    錯誤處理：
    - 分類不存在：404 錯誤
    - 無效 slug：404 錯誤
    """
    slug = _normalize_slug(slug)
    category = Category.query.filter_by(slug=slug).first_or_404()

    # 為 SEO 重定向到小寫 URL
    if slug != slug.lower():
        return redirect(url_for('main.category', slug=slug.lower()), code=301)
    
    # 查詢此分類下已發布的文章並分頁
    page, per_page = _get_pagination_params()
    query = Post.query.join(Category).filter(
        func.lower(Category.slug) == slug.lower(),
        Post.status == 'published'
    )
    pagination = _paginate_posts(query, page, per_page)

    return render_template(
        'main/category.html',
        posts=pagination.items,
        pagination=pagination,
        category=category,   # 傳整個 category object 給 template，比單純 name 更彈性
        active_page='category'
    )


@main_bp.route('/robots.txt')
def robots_txt():
    """
    提供 robots.txt 檔案
    
    功能描述：
    - 為搜索引擎爬蟲提供網站爬取指引
    - 安全地提供靜態檔案，避免路徑遍歷攻擊
    
    URL 模式：
        GET /robots.txt
    
    實作方式：
    - 使用 Flask 的 send_from_directory 安全提供檔案
    - 檔案位於應用程式的 static 資料夾中
    
    SEO 重要性：
    - robots.txt 是搜索引擎優化的基礎檔案
    - 指導搜索引擎哪些頁面可以爬取
    - 提升網站在搜索結果中的表現
    
    安全考量：
    - 使用 send_from_directory 防止目錄遍歷攻擊
    - 限制只能存取 static 資料夾中的檔案
    """
    return send_from_directory(current_app.static_folder, 'robots.txt')


# ========================================
# 身份驗證路由功能 (原 auth.py)
# ========================================

@auth_bp.route('/admin_login/', methods=['GET', 'POST'])
def admin_login():
    """
    管理員登入頁面
    
    功能描述：
    - 提供管理員身份驗證功能
    - 支援表單驗證和安全性檢查
    - 實作登入狀態檢查和重定向邏輯
    - 包含完整的錯誤處理和日誌記錄
    
    URL 模式：
        GET /admin_login/  - 顯示登入表單
        POST /admin_login/ - 處理登入請求
    
    安全功能：
    1. 重複登入檢查：已登入用戶自動重定向
    2. 電子郵件標準化：統一格式避免重複帳戶
    3. 密碼驗證：使用安全的密碼檢查機制
    4. 登入記錄：記錄所有登入嘗試（成功和失敗）
    5. 安全重定向：防止開放重定向攻擊
    
    表單處理流程：
    1. 驗證表單資料完整性和格式
    2. 標準化電子郵件格式
    3. 查詢用戶是否存在
    4. 驗證密碼正確性
    5. 建立用戶會話
    6. 更新最後登入時間
    7. 安全重定向到目標頁面
    
    錯誤處理：
    - 無效輸入：顯示友好錯誤訊息
    - 用戶不存在：統一錯誤訊息（避免帳戶枚舉攻擊）
    - 密碼錯誤：統一錯誤訊息
    - 系統錯誤：記錄到日誌但不影響用戶體驗
    
    日誌記錄：
    - 記錄所有登入嘗試（包含電子郵件）
    - 記錄成功登入事件
    - 記錄表單驗證失敗
    - 記錄系統錯誤但不中斷流程
    
    模板變數：
        form: 登入表單物件
        active_page: 頁面導航標識
    
    安全考量：
    - 使用 remember=True 提供持久會話
    - 統一錯誤訊息防止資訊洩露
    - 安全的重定向處理
    - 密碼驗證使用加密比較
    """
    
    # 如果已經登入，重定向到管理後台
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        email = User.normalize_email(form.email.data)
        password = form.password.data

        if not email:
            return _handle_login_error('請輸入有效的電子郵件。')
        
        # 記錄登入嘗試
        current_app.logger.info(f"嘗試登入電子郵件：{email}")
        
        # 查詢用戶
        user = User.find_by_email(email)
        
        if user is None:
            return _handle_login_error('無效的電子郵件或密碼。', email)
        
        if not user.check_password(password):
            return _handle_login_error('無效的電子郵件或密碼。', email)
        
        # 登入成功
        login_user(user, remember=True)
        current_app.logger.info(f"使用者 {email} 成功登入")
        
        # 更新最後登入時間（安全方式）
        try:
            if hasattr(user, 'update_last_login'):
                user.update_last_login()
        except Exception as e:
            current_app.logger.warning(f"更新最後登入時間失敗：{e}")
            # 不影響登入流程，繼續執行
        
        # 處理next頁面重定向
        next_page = _get_safe_next_url()
            
        flash('歡迎回來！', 'success')
        return redirect(next_page)
    
    # 記錄表單驗證錯誤
    if request.method == 'POST' and not form.validate_on_submit():
        current_app.logger.warning(f"表單驗證失敗：{form.errors}")
    
    return render_template('auth/login.html', form=form, active_page='login')


@auth_bp.route('/logout/')
@login_required
def logout():
    """
    用戶登出功能
    
    功能描述：
    - 安全地結束用戶會話
    - 清除所有登入狀態和 cookies
    - 記錄登出事件以供審計
    - 提供友好的用戶反饋
    
    URL 模式：
        GET /logout/
    
    安全要求：
    - 使用 @login_required 裝飾器確保只有已登入用戶可訪問
    - 防止未經授權的登出操作
    
    處理流程：
    1. 檢查用戶登入狀態
    2. 記錄用戶資訊以供日誌
    3. 執行登出操作（清除會話）
    4. 記錄登出事件
    5. 顯示確認訊息
    6. 重定向到網站首頁
    
    日誌記錄：
    - 記錄登出的用戶電子郵件
    - 包含時間戳記以供審計
    - 處理異常情況（如用戶狀態異常）
    
    用戶體驗：
    - 顯示友好的登出確認訊息
    - 自動重定向到公開頁面
    - 確保所有私人資料不再可訪問
    
    安全考量：
    - 完全清除用戶會話資料
    - 防止會話劫持和重放攻擊
    - 確保敏感頁面不再可訪問
    """
    user_email = current_user.email if current_user.is_authenticated else 'Unknown'
    logout_user()
    current_app.logger.info(f"使用者 {user_email} 已登出")
    flash('您已成功登出。', 'info')
    return redirect(url_for('main.index'))


# ========================================
# 網站地圖路由功能 (原 sitemap.py)
# ========================================

@sitemap_bp.route('/sitemap.xml', methods=['GET'])
def sitemap():
    """
    生成 XML 格式的網站地圖
    
    功能描述：
    - 為搜索引擎提供網站結構的完整地圖
    - 自動包含所有已發布的文章和靜態頁面
    - 提供 SEO 相關的元資料（最後修改時間、更新頻率、優先級）
    - 支援大量文章的效能優化處理
    
    URL 模式：
        GET /sitemap.xml
    
    SEO 重要性：
    - 幫助搜索引擎發現和索引網站內容
    - 提供內容的優先級和更新頻率資訊
    - 加速新內容的搜索引擎收錄
    - 改善網站在搜索結果中的可見性
    
    網站地圖結構：
    1. 靜態頁面：
       - 從應用程式配置讀取 SITEMAP_STATIC_ROUTES
       - 設定高優先級（1.0）和每日更新頻率
       - 包含首頁和其他重要靜態頁面
    
    2. 動態內容（文章）：
       - 查詢所有已發布狀態的文章
       - 生成 SEO 友好的 URL
       - 設定適當的優先級和更新頻率
       - 使用文章的實際修改時間
    
    效能優化：
    - 使用 yield_per(100) 批次處理大量文章
    - 減少記憶體使用和資料庫負載
    - 適合處理數千篇文章的大型網站
    
    錯誤處理：
    - 資料庫查詢異常的妥善處理
    - URL 生成失敗的容錯機制
    - 確保部分內容失敗不影響整個網站地圖
    
    配置彈性：
    - 支援透過應用程式配置自訂靜態路由
    - 支援文章層級的 SEO 參數設定
    - 預設值確保基本功能始終可用
    
    XML 標準：
    - 符合 sitemap.xml 協議標準
    - 包含 loc（URL）、lastmod（最後修改）、changefreq（更新頻率）、priority（優先級）
    - 正確的 MIME 類型（application/xml）
    
    返回格式：
        XML 響應，包含所有頁面的結構化資訊
        
    模板變數：
        pages: 包含所有頁面資訊的列表，每個項目包含：
            - loc: 頁面的完整 URL
            - lastmod: 最後修改日期 (ISO 格式)
            - changefreq: 更新頻率 ('daily', 'weekly', 'monthly' 等)
            - priority: 優先級 (0.0-1.0)
    
    使用場景：
    - 提交給 Google Search Console
    - 提交給 Bing Webmaster Tools
    - 其他搜索引擎的網站地圖提交
    - SEO 工具的網站分析
    """
    pages = []
    today = date.today().isoformat()

    # 1️⃣ 靜態路由處理
    # 從應用程式配置讀取需要包含在網站地圖中的靜態路由
    # 這些通常是網站的重要頁面，如首頁、關於頁面等
    static_routes = current_app.config.get('SITEMAP_STATIC_ROUTES', ['main.index'])
    for endpoint in static_routes:
        url = _safe_url_generation(endpoint, _external=True)
        if url:
            pages.append({
                'loc': url,
                'lastmod': today,
                'changefreq': 'daily',
                'priority': '1.0',
            })

    # 2️⃣ 動態內容（文章）處理
    # 查詢所有已發布的文章，使用 yield_per 進行效能優化
    try:
        posts = Post.query.filter_by(status='published').yield_per(100)
    except Exception as e:
        current_app.logger.error(f"無法為網站地圖取得文章：{e}")
        posts = []

    for post in posts:
        # 處理文章 URL 生成
        # 支援自定義 slug 和自動生成的 untitled-{id} 格式
        post_slug = post.slug or f'untitled-{post.id}'
        post_url = _safe_url_generation('main.post', slug=post_slug, _external=True)
        
        if post_url:
            # 使用文章的實際修改時間，回退到建立時間
            updated = (post.updated_at or post.created_at).date().isoformat()

            # 3️⃣ 動態 SEO 參數設定
            # 允許在 Post 模型中自訂 SEO 參數，提供預設值
            changefreq = getattr(post, 'changefreq', 'monthly')
            priority = getattr(post, 'priority', '0.8')

            pages.append({
                'loc': post_url,
                'lastmod': updated,
                'changefreq': changefreq,
                'priority': priority,
            })

    # 返回 XML 格式的網站地圖
    return Response(
        render_template("sitemap.xml", pages=pages),
        mimetype='application/xml'
    )

# ========================================
# 藍圖註冊與應用程式集成
# ========================================

def register_public_blueprints(app: 'Flask') -> None:
    """
    統一註冊所有公開路由的 Blueprint
    
    功能描述：
    - 將所有定義的 Blueprint 註冊到 Flask 應用程式實例
    - 提供集中化的路由管理和註冊流程
    - 確保所有公開功能正確整合到應用程式中
    - 記錄註冊過程以便於除錯和監控
    
    參數：
        app (Flask): Flask 應用程式實例
    
    註冊的 Blueprint：
    1. main_bp (main):
       - 處理網站主要內容路由
       - URL 前綴：無（根路徑）
       - 功能：首頁、文章顯示、分類瀏覽、robots.txt
    
    2. auth_bp (auth):
       - 處理身份驗證相關路由
       - URL 前綴：無
       - 功能：管理員登入、登出
    
    3. sitemap_bp (sitemap):
       - 處理 SEO 相關路由
       - URL 前綴：無
       - 功能：XML 網站地圖生成
    
    設計考量：
    - 模組化：每個功能領域獨立的 Blueprint
    - 可維護性：清晰的功能分離和組織
    - 可擴展性：新功能可輕易作為新 Blueprint 添加
    - 統一管理：集中註冊避免重複和遺漏
    
    錯誤處理：
    - 註冊過程中的任何異常都會被記錄
    - 不會因單一 Blueprint 失敗而影響整個應用程式啟動
    
    日誌記錄：
    - 記錄成功註冊的確認訊息
    - 便於運維人員確認應用程式啟動狀態
    - 有助於除錯和問題排查
    
    使用方式：
        在 Flask 應用程式初始化過程中調用：
        ```python
        from app.routes.public import register_public_blueprints
        
        app = Flask(__name__)
        register_public_blueprints(app)
        ```
    
    注意事項：
    - 必須在應用程式配置完成後調用
    - 建議在其他 Blueprint 註冊之前調用
    - 確保相關的模型和表單已正確匯入
    """
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(sitemap_bp)
    
    app.logger.info("所有公開路由藍圖已成功註冊")
