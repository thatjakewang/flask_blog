from flask import Blueprint, render_template, request, redirect, url_for
from app.models import Post, Page, Tag
from flask_login import current_user
from app import db
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts, now = datetime.now())

@bp.route('/tag/<slug>')
def tag(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    posts = tag.posts
    return render_template('tag.html', tag=tag, posts=posts)

@bp.route('/<slug>')
def dynamic_page(slug):
    page_query = Page.query.filter_by(slug=slug)
    post_query = Post.query.filter_by(slug=slug)
    
    if not current_user.is_authenticated:
        page_query = page_query.filter_by(published=True)
        post_query = post_query.filter_by(published=True)
    
    page = page_query.first()
    if page:
        return render_template('page.html', page=page)

    post = post_query.first_or_404()
    return render_template('dashboard/post.html', post=post)