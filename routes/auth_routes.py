"""
Authentication Blueprint
------------------------
Handles login, signup, profile management, password changes,
2FA verification, support requests, and file uploads.
"""

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

from flask import session  # ✅ Add this import at the top with others
from datetime import timedelta  # ✅ If not already added in app configuration


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login with optional 2FA verification."""
    form = LoginForm()
    
    if form.validate_on_submit():
        try:
            identifier = form.identifier.data
            user = User.query.filter(
                (User.email == identifier) | (User.phone_number == identifier)
            ).first()

            if not user:
                flash("Email or phone number not recognized.", "danger")
                return render_template("login.html", form=form)

            if not user.check_password(form.password.data):
                flash("Incorrect password.", "danger")
                return render_template("login.html", form=form)

            # ✅ 2FA logic stays the same
            if user.two_factor_enabled:
                if not form.two_factor_code.data:
                    flash("2FA code required.", "warning")
                    return render_template("login.html", form=form, requires_2fa=True)
                if not verify_2fa_code(user, form.two_factor_code.data):
                    flash("Invalid 2FA code.", "danger")
                    return render_template("login.html", form=form)

            login_user(user, remember=form.remember_me.data)

            # ✅ This enables session timeout tracking
            session.permanent = True  

            flash("Login successful.", "success")
            logger.debug(f"User {identifier} logged in.")

            return redirect(url_for(f"{user.role}.dashboard")) if user.role in [
                "tenant", "landlord", "service", "admin"
            ] else redirect(url_for("portal"))

        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            flash("An error occurred during login. Try again.", "danger")

    return render_template("login.html", form=form)



@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """User registration with optional profile picture."""
    form = SignupForm()
    if form.validate_on_submit():
        try:
            full_phone = f"+254{form.phone_number.data}"
            profile_picture_path = save_profile_picture(form.profile_picture.data)

            user = User(
                name=form.full_name.data,
                email=form.email.data,
                phone_number=full_phone,
                role=form.role.data,
                mpesa_details=form.mpesa_details.data if form.role.data in ["landlord", "service"] else None,
                profile_picture=profile_picture_path,
                language=form.language.data,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()

            flash("Account created. Please login.", "success")
            logger.debug(f"User {form.email.data} created.")
            return redirect(url_for("auth.login"))

        except IntegrityError:
            db.session.rollback()
            flash("Email or phone already registered.", "danger")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Signup error: {e}", exc_info=True)
            flash("Error creating account. Try again.", "danger")

    return render_template("signup.html", form=form)


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