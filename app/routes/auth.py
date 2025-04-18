from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db

bp = Blueprint('auth', __name__)

@bp.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('無效的用戶名或密碼')
            return redirect(url_for('auth.admin_login'))
        
        login_user(user)
        return redirect(url_for('dashboard.index')) 
    
    return render_template('auth/login.html')
 
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))