from flask import Blueprint, render_template, redirect, request, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from models.models import User
from extensions import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('auth.login'))
        flash('Invalid credentials')
    return render_template('login.html')
#else:
 #    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        hashed_password = generate_password_hash(request.form['password'])
        user = User(
            name=request.form['name'],
            email=request.form['email'],
            password=hashed_password,
            role=request.form['role']
        )
        db.session.add(user)
        db.session.commit()
        flash('Account created, please login.')
        return redirect(url_for('auth.signup'))
    return render_template('signup.html')
# LOGOUT
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
# PROFILE UPDATE
@auth_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    current_user.name = request.form['name']
    current_user.email = request.form['email']
    db.session.commit()
    flash("Profile updated!")
    return redirect(url_for('auth.profile'))
# PROFILE PAGE
@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


# from flask import current_app
# print("Using app:", current_app.name)
