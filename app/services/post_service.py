# -*- coding: utf-8 -*-
"""
文章服務

處理文章相關的業務邏輯，包括建立、更新和驗證
"""
from typing import Dict, Any
from flask import current_app
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from app.models import Post, db
from app.utils import clean_html_content
from app.services.category_service import CategoryService
from app.services.statistics_service import StatisticsService


class PostService:
    """處理文章操作的服務類別"""
    
    @staticmethod
    def create_post(form_data: Dict[str, Any], action: str) -> Dict[str, Any]:
        """建立新文章
        
        參數:
            form_data: 包含表單資料的字典
            action: 操作類型（'publish'、'save' 或預設為 'draft'）
            
        回傳:
            包含成功狀態、訊息和文章編號（如果成功）的字典
        """
        
        # 取得分類編號，或如果未提供則指定預設分類
        category_id = form_data.get('category_id')
        if not category_id or category_id == 0:
            default_category = CategoryService.get_or_create_default_category()
            category_id = default_category.id
        
        status = 'published' if action == 'publish' else 'draft'

        # 建立新文章
        post = Post(
            title=form_data.get('title'),
            slug=form_data.get('slug', '').lower(),
            thumbnail=form_data.get('thumbnail'),
            description=form_data.get('description'),
            content=form_data.get('content', ''),
            category_id=category_id,
            status=status,
            author_id=current_user.id
        )
        
        current_app.logger.info(
            f"建立文章：標題={form_data.get('title')}, 狀態={status}, "
            f"分類編號={category_id}"
        )
        
        db.session.add(post)
        
        
        try:
            db.session.commit()
            
            # 清除快取
            CategoryService.clear_category_cache()
            StatisticsService.clear_stats_cache()
        
            return {
                'success': True,
                'message': f'文章{"發布" if status == "published" else "儲存"}成功！',
                'post_id': post.id,
                'post_slug': post.slug,
                'status': status
            }
            
        except IntegrityError as e:
            db.session.rollback()
            error_msg = "此網址代碼已被使用，請選擇其他代碼。" if 'slug' in str(e).lower() else "資料庫錯誤，請稍後再試。"
            current_app.logger.error(f"建立文章時資料庫錯誤：{e}")
            
            return {
                'success': False,
                'message': error_msg,
                'error_type': 'integrity' if 'slug' in str(e).lower() else 'database'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"建立文章時發生非預期錯誤：{e}")
            
            return {
                'success': False,
                'message': f'發生錯誤：{str(e)}',
                'error_type': 'unexpected'
            }
    
    @staticmethod
    def update_post(post: Post, form_data: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Update an existing post
        
        Args:
            post: Post object to update
            form_data: Dictionary containing form data
            action: Action type ('publish', 'save')
            
        Returns:
            Dictionary containing success status and message
        """
        # Determine post status
        if action == 'publish':
            post.status = 'published'
        elif action == 'save':
            post.status = 'draft'
        elif action == 'update':
            # 保持原有狀態，不改變 post.status
            pass
        
        # 取得分類編號，或如果未提供則指定預設分類
        category_id = form_data.get('category_id')
        if not category_id or category_id == 0:
            default_category = CategoryService.get_or_create_default_category()
            category_id = default_category.id
        
        # Update post data
        post.title = form_data.get('title')
        post.slug = form_data.get('slug', '').lower()
        post.thumbnail = form_data.get('thumbnail')
        post.description = form_data.get('description')
        post.content = form_data.get('content', '')
        post.category_id = category_id
        
        current_app.logger.info(f"更新文章 {post.id}：狀態={post.status}")
        
        try:
            db.session.commit()
            
            # 清除快取
            CategoryService.clear_category_cache()
            StatisticsService.clear_stats_cache()
            
            return {
                'success': True,
                'message': f'文章{"發布" if post.status == "published" else "更新"}成功！',
                'post_id': post.id,
                'post_slug': post.slug,
                'status': post.status
            }
            
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"更新文章時資料庫錯誤：{e}")
            
            return {
                'success': False,
                'message': "此 slug 已被使用，請選擇其他 slug。",
                'error_type': 'integrity'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"更新文章時發生錯誤：{e}")
            
            return {
                'success': False,
                'message': f'發生錯誤：{str(e)}',
                'error_type': 'unexpected'
            }
    
    @staticmethod
    def delete_post(post: Post) -> Dict[str, Any]:
        """Delete a post
        
        Args:
            post: Post object to delete
            
        Returns:
            Dictionary containing success status and message
        """
        try:
            post_id = post.id
            db.session.delete(post)
            db.session.commit()
            
            # 清除快取
            CategoryService.clear_category_cache()
            StatisticsService.clear_stats_cache()
            
            current_app.logger.info(f"文章 {post_id} 由使用者 {current_user.id} 刪除")
            
            return {
                'success': True,
                'message': '文章刪除成功！'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"刪除文章時發生錯誤：{e}")
            
            return {
                'success': False,
                'message': f'刪除失敗：{str(e)}'
            }
    
    @staticmethod
    def check_post_permission(post: Post, user) -> bool:
        """Check if user has permission to modify post
        
        Args:
            post: Post object
            user: User object
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        return post.author_id == user.id or (hasattr(user, 'is_admin') and user.is_admin)
