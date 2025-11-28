from flask import session, request  # ✅ Add this import at the top with others
from datetime import timedelta  # ✅ If not already added in app configuration

"""
Authentication Blueprint
------------------------
Handles login, signup, profile management, password changes,
2FA verification, support requests, and file uploads.
"""
import random
import string
#from flask import session, request
# =========================
# 📦 Standard Library Imports
# =========================
import os
import re
import logging
from datetime import datetime
from flask import Blueprint, session, jsonify
from datetime import timedelta

# =========================
# 🌐 Third-party Imports
# =========================
from flask import (
    Blueprint, jsonify, render_template, redirect,
    request, url_for, flash, current_app as app
)
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, FileField,
    BooleanField, SelectField
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
import pyotp

# =========================
# 🧱 Project Imports
# =========================
from models.models import User
from extensions import db

# =========================
# 📝 Logging Setup
# =========================
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# =========================
# 📍 Blueprint Declaration
# =========================
auth_bp = Blueprint("auth", __name__)

# =========================
# 🧾 Form Classes
# =========================

class LoginForm(FlaskForm):
    identifier = StringField('Email or Phone', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    two_factor_code = StringField('2FA Code')
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')


class SignupForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number', validators=[
        DataRequired(),
        Regexp(r'^\d{9}$', message="Phone number must be 9 digits after +254")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters"),
        Regexp(
            r'^(?=.*[a-zA-Z])(?=.*\d)(?=.*[!@#$%^&*()_\-=\[\]{};:\'\"\\|,.<>/?]).*$',
            message="Password must include a digit and special character"
        )
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message="Passwords must match")
    ])
    role = SelectField('Role', choices=[
        ('tenant', 'Tenant'),
        ('landlord', 'Landlord'),
        ('service', 'Service Provider'),
        ('admin', 'Admin')
    ], validators=[DataRequired()])
    mpesa_details = StringField('M-Pesa Details')
    profile_picture = FileField('Profile Picture')
    language = SelectField('Language', choices=[
        ('en', 'English'),
        ('sw', 'Swahili')
    ], default='en')
    terms = BooleanField('I accept the terms and conditions', validators=[DataRequired()])
    submit = SubmitField('Sign Up')


class ForgotPasswordForm(FlaskForm):
    identifier = StringField('Email or Phone', validators=[DataRequired()])
    submit = SubmitField('Request Reset')


class SupportForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    message = StringField('Message', validators=[DataRequired()])
    submit = SubmitField('Submit')


class ProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[
        Regexp(r'^(?:\+254)?\d{9}$', message="Phone number must be 9 digits (with optional +254)")
    ])
    location = StringField('Location')
    bio = StringField('Bio')
    submit = SubmitField('Save Changes')


class PasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters long"),
        Regexp(
            r'^(?=.*[a-zA-Z])(?=.*\d)(?=.*[!@#$%^&*()_\-=\[\]{};:\'\"\\|,.<>/?]).*$',
            message="Password must include a digit and special character"
        )
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message="Passwords must match")
    ])
    submit = SubmitField('Update Password')


# =========================
# 🔐 Authentication Routes
# =========================

# from flask import session  # ✅ Add this import at the top with others
# from datetime import timedelta  # ✅ If not already added in app configuration


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # 1. If already logged in, redirect to the portal route
    if current_user.is_authenticated:
        # Do not call the function directly. Use redirect.
        # The 'portal' function in app.py handles the role logic.
        return redirect(url_for('portal'))

    form = LoginForm()
    
    if form.validate_on_submit():
        identifier = form.identifier.data
        password = form.password.data
        remember = form.remember_me.data
        
        # 2. Find user
        user = User.query.filter(
            (User.email == identifier) | (User.phone_number == identifier)
        ).first()

        # 3. Check Password
        if not user or not user.check_password(password):
            flash('Incorrect email/phone or password.', category='danger')
            return render_template('login.html', form=form)

        # 4. CRITICAL: Check Email Verification
        if not user.is_verified:
            flash('Please verify your email address before logging in.', category='warning')
            # Set session variable so verify route knows who it is
            session['email_to_verify'] = user.email
            return redirect(url_for('auth.verify_email'))

        # 5. Check Two-Factor Authentication (2FA)
        if user.two_factor_enabled:
            # Check if code was entered in the form
            code = form.two_factor_code.data
            
            if code:
                # Verify the code using your helper function
                if verify_2fa_code(user, code):
                    login_user(user, remember=remember)
                    session.permanent = True
                    flash('Logged in successfully!', category='success')
                    return redirect(url_for('portal'))
                else:
                    flash('Invalid 2FA code. Please try again.', category='danger')
                    # We return the template but keep the identifier filled in
                    return render_template('login.html', form=form, show_2fa=True)
            else:
                # 2FA is enabled but code box was empty or hidden.
                # Re-render login page with 'show_2fa' flag to unhide the input box
                flash('Two-Factor Authentication is enabled. Enter your code.', category='info')
                return render_template('login.html', form=form, show_2fa=True)

        # 6. Standard Login (No 2FA)
        login_user(user, remember=remember)
        session.permanent = True
        flash('Logged in successfully!', category='success')
        
        # Redirect to the main portal route
        return redirect(url_for('portal'))

    return render_template('login.html', form=form)

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """User registration with email verification step."""
    form = SignupForm()
    if form.validate_on_submit():
        try:
            full_phone = f"+254{form.phone_number.data}"
            
            # 1. Check if user already exists
            if User.query.filter((User.email == form.email.data) | (User.phone_number == full_phone)).first():
                flash("Email or phone already registered.", "danger")
                return render_template("signup.html", form=form)

            # 2. Handle Profile Picture
            profile_picture_path = save_profile_picture(form.profile_picture.data)

            # 3. Generate 6-digit OTP
            otp = ''.join(random.choices(string.digits, k=6))

            # 4. Create User (Marked as NOT verified)
            user = User(
                name=form.full_name.data,
                email=form.email.data,
                phone_number=full_phone,
                role=form.role.data,
                mpesa_details=form.mpesa_details.data if form.role.data in ["landlord", "service"] else None,
                profile_picture=profile_picture_path,
                language=form.language.data,
                is_verified=False,      # <--- Important: User is not active yet
                verification_code=otp   # <--- Store the code
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()

            # 5. Simulate Sending Email (Replace with Flask-Mail in production)
            print(f"============================================")
            print(f"SENDING EMAIL TO: {user.email}")
            print(f"VERIFICATION CODE: {otp}")
            print(f"============================================")

            # 6. Store email in session so verify route knows who it is
            session['email_to_verify'] = user.email
            
            flash("Account created! Please check your email for the verification code.", "info")
            
            # 7. Redirect to Verification Page (NOT Login)
            return redirect(url_for("auth.verify_email"))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Signup error: {e}", exc_info=True)
            flash("Error creating account. Try again.", "danger")

    return render_template("signup.html", form=form)


@auth_bp.route("/verify_email", methods=["GET", "POST"])
def verify_email():
    """Handles the one-time email verification code."""
    # Get the email of the user trying to verify
    email = session.get('email_to_verify')
    
    # If session expired or direct access, send to login
    if not email:
        return redirect(url_for('auth.login'))
        
    # We don't necessarily need a WTForm class for this simple logic, 
    # but we need to handle the POST request from the 6-digit input.
    if request.method == "POST":
        submitted_code = request.form.get('code')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.verification_code == submitted_code:
            # Code matches! Verify user.
            user.is_verified = True
            user.verification_code = None # Clear code for security
            db.session.commit()
            
            # Clear the session variable
            session.pop('email_to_verify', None)
            
            flash("Email verified successfully! You can now log in.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash("Invalid or expired verification code.", "danger")

    return render_template("verify_email.html", email=email)


@auth_bp.route("/resend_verification")
def resend_verification():
    """Resends the OTP to the user in the session."""
    email = session.get('email_to_verify')
    if not email:
        flash("Session expired. Please log in.", "warning")
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(email=email).first()
    if user:
        # Generate new code
        otp = ''.join(random.choices(string.digits, k=6))
        user.verification_code = otp
        db.session.commit()
        
        print(f"RESENT CODE FOR {email}: {otp}")
        flash(f"A new code has been sent to {email}", "success")
        
    return redirect(url_for('auth.verify_email'))


@auth_bp.route("/logout")
@login_required
def logout():
    """Logs out the current user."""
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))


# =========================
# 🔑 Password & Profile Routes
# =========================

@auth_bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    """Handles password reset requests."""
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter(
            (User.email == form.identifier.data) | (User.phone_number == form.identifier.data)
        ).first()
        if not user:
            flash("Email/phone not found.", "danger")
        else:
            # TODO: Send actual reset link (email/SMS)
            flash("Password reset link sent.", "success")
            logger.debug(f"Password reset requested for {form.identifier.data}")
            return redirect(url_for("auth.login"))
    return render_template("forgot_password.html", form=form)


@auth_bp.route("/profile")
@login_required
def profile():
    """Displays the user's profile."""
    return render_template("profile.html", user=current_user)


@auth_bp.route("/update_profile", methods=["POST"])
@login_required
def update_profile():
    """Updates user profile information."""
    form = ProfileForm()
    if form.validate_on_submit():
        try:
            current_user.name = form.name.data
            current_user.email = form.email.data
            phone = form.phone.data
            current_user.phone_number = phone if phone.startswith("+254") else f"+254{phone}"
            current_user.location = form.location.data
            current_user.bio = form.bio.data

            db.session.commit()
            logger.info(f"User {current_user.id} updated profile")
            return jsonify({'success': True, 'message': 'Profile updated successfully'})

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating profile: {e}")
            return jsonify({'success': False, 'message': 'Error updating profile'}), 500

    errors = {field: errors[0] for field, errors in form.errors.items()}
    return jsonify({'success': False, 'message': 'Invalid form data', 'errors': errors}), 400


@auth_bp.route("/change_password", methods=["POST"])
@login_required
def change_password():
    """Allows the user to change their password."""
    form = PasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            logger.warning(f"Invalid current password for user {current_user.id}")
            return jsonify({'success': False, 'message': 'Current password is incorrect'}), 400

        try:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            logger.info(f"User {current_user.id} changed password")
            return jsonify({'success': True, 'message': 'Password updated successfully'})
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error changing password: {e}")
            return jsonify({'success': False, 'message': 'Error updating password'}), 500

    errors = {field: errors[0] for field, errors in form.errors.items()}
    return jsonify({'success': False, 'message': 'Invalid form data', 'errors': errors}), 400


# =========================
# 📎 File Uploads
# =========================

@auth_bp.route('/upload_profile_picture', methods=['POST'])
@login_required
def upload_profile_picture():
    """Handles profile picture uploads."""
    form = ProfileForm()  # For CSRF validation

    if not form.validate():
        logger.warning(f"CSRF validation failed for user {current_user.id}")
        return jsonify({'success': False, 'message': 'Invalid CSRF token'}), 400

    file = request.files.get('profile_picture')
    if not file or file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400

    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    if not '.' in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return jsonify({'success': False, 'message': 'Invalid file type'}), 400

    if file.content_length and file.content_length > 5 * 1024 * 1024:
        return jsonify({'success': False, 'message': 'File size exceeds 5MB'}), 400

    try:
        filename = secure_filename(file.filename)
        unique_filename = f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{filename}"
        upload_folder = os.path.join(app.root_path, 'static', 'images')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)

        current_user.profile_picture = f"images/{unique_filename}"
        db.session.commit()

        logger.info(f"User {current_user.id} uploaded profile picture: {unique_filename}")
        return jsonify({'success': True, 'message': 'Profile picture updated', 'filename': current_user.profile_picture})

    except Exception as e:
        logger.error(f"Error uploading profile picture: {e}")
        return jsonify({'success': False, 'message': 'Error uploading profile picture'}), 500


# =========================
# 📞 Support & Misc
# =========================

@auth_bp.route("/support", methods=["GET", "POST"])
def support():
    """Handles support form submissions."""
    form = SupportForm()
    if form.validate_on_submit():
        try:
            # TODO: Save support to DB or email admin
            flash("Support request submitted. We'll contact you.", "success")
            logger.debug(f"Support request from {form.email.data}")
            return redirect(url_for("auth.support"))
        except Exception as e:
            logger.error(f"Support form error: {e}")
            flash("Error submitting support request.", "danger")

    return render_template("support.html", form=form)


@auth_bp.route("/terms")
def terms():
    """Displays terms and conditions."""
    return render_template("terms.html")


# =========================
# 🧠 Helper Functions
# =========================

def verify_2fa_code(user, code):
    """Verifies a given 2FA code against the user's TOTP secret."""
    try:
        totp = pyotp.TOTP(user.two_factor_secret)
        return totp.verify(code)
    except Exception as e:
        logger.error(f"2FA verification error for user {user.email}: {e}", exc_info=True)
        return False


def save_profile_picture(file):
    """Saves a profile picture file to the static folder and returns the relative path."""
    if not file:
        return None

    filename = secure_filename(file.filename)
    upload_folder = os.path.join(app.root_path, "static", "images")
    os.makedirs(upload_folder, exist_ok=True)

    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)

    return f"images/{filename}"


@auth_bp.route('/refresh-session', methods=['POST'])
def refresh_session():
    session.permanent = True  # refresh cookie expiration
    return jsonify({"status": "refreshed"})