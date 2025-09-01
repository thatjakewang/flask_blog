# -*- coding: utf-8 -*-
"""
Statistics Service

Handles dashboard statistics and counts
"""
from app.models import Post, Category
from app import cache


class StatisticsService:
    """Service for handling dashboard statistics"""
    
    @staticmethod
    @cache.memoize(timeout=300, make_name=lambda fname: f'blog_stats_{fname}')  # 快取 5 分鐘
    def get_dashboard_stats():
        """Get dashboard statistics including post and category counts
        
        Returns:
            dict: Dictionary containing posts_count, drafts_count, categories_count
        """
        return {
            'posts_count': Post.query.filter_by(status='published').count(),
            'drafts_count': Post.query.filter_by(status='draft').count(),
            'categories_count': Category.query.count()
        }
    
    @staticmethod
    def clear_stats_cache():
        """Clear statistics cache"""
        cache.delete_memoized(StatisticsService.get_dashboard_stats)