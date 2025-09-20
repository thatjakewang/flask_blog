# -*- coding: utf-8 -*-
"""
Category Service

Handles category-related business logic
"""
from typing import List, Tuple, Optional
from app.models import Category
from app import cache


class CategoryService:
    """Service for handling category operations"""
    
    @staticmethod
    @cache.memoize(timeout=300, make_name=lambda fname: f'blog_category_choices_{fname}')
    def get_category_choices() -> List[Tuple[int, str]]:
        """Get category choices for forms
        
        Returns:
            List of tuples containing (category_id, category_name)
        """
        categories = Category.query.all()
        return [(0, '選擇分類')] + [(c.id, c.name) for c in categories]
    
    @staticmethod
    def has_categories() -> bool:
        """Check if any categories exist
        
        Returns:
            bool: True if categories exist, False otherwise
        """
        return Category.query.count() > 0
    
    @staticmethod
    def get_category_by_id(category_id: int) -> Optional[Category]:
        """Get category by ID
        
        Args:
            category_id: Category ID to look up
            
        Returns:
            Category object or None if not found
        """
        if category_id == 0:
            return None
        return Category.query.get(category_id)
    
    @staticmethod
    def validate_category_id(category_id: int) -> bool:
        """Validate if category ID exists and is not the default (0)
        
        Args:
            category_id: Category ID to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if category_id == 0:
            return False
        return Category.query.get(category_id) is not None
    
    @staticmethod
    def clear_category_cache():
        """Clear category-related caches"""
        cache.delete('blog_available_categories')
        cache.delete('blog_category_choices')
        cache.delete('nav_available_categories')
        cache.delete_memoized(CategoryService.get_category_choices)
        
        # 也清除統計快取，因為分類數量可能已改變
        from app.services.statistics_service import StatisticsService
        StatisticsService.clear_stats_cache()

    @staticmethod
    def get_or_create_default_category() -> Category:
        """
        Get the default 'Uncategorized' category, creating it if it doesn't exist.
        """
        from app import db
        default_slug = 'uncategorized'
        default_category = Category.query.filter_by(slug=default_slug).first()
        
        if not default_category:
            default_category = Category(
                name='Uncategorized',
                slug=default_slug,
                description='Default category for posts without a specific category.'
            )
            db.session.add(default_category)
            # Flush the session to get an ID for the new category, but don't commit yet.
            # The calling function (e.g., create_post) will handle the commit.
            db.session.flush()
            CategoryService.clear_category_cache()
                
        return default_category
