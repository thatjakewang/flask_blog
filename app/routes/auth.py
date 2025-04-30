from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.forms import LoginForm

bp = Blueprint('auth', __name__)

@bp.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid Email or password.')
            return redirect(url_for('auth.admin_login'))
        login_user(user)
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/login.html', form=form)
 
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))