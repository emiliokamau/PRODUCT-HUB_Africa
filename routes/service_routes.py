from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.models import ServiceProvider, ServiceRequest, Appointment, Review, User
from extensions import db
from sqlalchemy import func, extract
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os

service_provider_bp = Blueprint('service_provider', __name__, url_prefix='/service_provider')

@service_provider_bp.route('/dashboard')
@login_required
def dashboard():
    # Get service provider profile
    provider = ServiceProvider.query.filter_by(user_id=current_user.id).first()
    
    if not provider:
        flash('Please complete your service provider profile first.', 'warning')
        return redirect(url_for('service_provider.profile'))
    
    # Get counts
    pending_requests_count = ServiceRequest.query.filter_by(
        service_provider_id=provider.id, 
        status='pending'
    ).count()
    
    completed_jobs_count = ServiceRequest.query.filter_by(
        service_provider_id=provider.id, 
        status='completed'
    ).count()
    
    # Get monthly earnings
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_earnings = db.session.query(
        func.sum(ServiceRequest.amount)
    ).filter(
        ServiceRequest.service_provider_id == provider.id,
        ServiceRequest.status == 'completed',
        extract('month', ServiceRequest.completed_at) == current_month,
        extract('year', ServiceRequest.completed_at) == current_year
    ).scalar() or 0
    
    # Get average rating
    average_rating = db.session.query(
        func.avg(Review.rating)
    ).filter_by(service_provider_id=provider.id).scalar() or 0
    
    # Get recent requests
    recent_requests = ServiceRequest.query.filter_by(
        service_provider_id=provider.id
    ).order_by(ServiceRequest.created_at.desc()).limit(5).all()
    
    # Get upcoming appointments
    upcoming_appointments = Appointment.query.filter(
        Appointment.service_provider_id == provider.id,
        Appointment.date >= datetime.now()
    ).order_by(Appointment.date).limit(5).all()
    
    # Get recent reviews
    recent_reviews = Review.query.filter_by(
        service_provider_id=provider.id
    ).order_by(Review.created_at.desc()).limit(3).all()
    
    # Get earnings data for chart
    earnings_labels = []
    earnings_data = []
    
    # Get data for the last 30 days
    for i in range(30, 0, -1):
        date = datetime.now() - timedelta(days=i)
        earnings_labels.append(date.strftime('%b %d'))
        
        daily_earnings = db.session.query(
            func.sum(ServiceRequest.amount)
        ).filter(
            ServiceRequest.service_provider_id == provider.id,
            ServiceRequest.status == 'completed',
            func.date(ServiceRequest.completed_at) == date.date()
        ).scalar() or 0
        
        earnings_data.append(float(daily_earnings))
    
    # Get notifications (placeholder - in a real app, this would come from a notifications table)
    notifications = []
    
    return render_template(
        'service_provider_dashboard.html',
        pending_requests_count=pending_requests_count,
        completed_jobs_count=completed_jobs_count,
        monthly_earnings=monthly_earnings,
        average_rating=average_rating,
        recent_requests=recent_requests,
        upcoming_appointments=upcoming_appointments,
        recent_reviews=recent_reviews,
        earnings_labels=earnings_labels,
        earnings_data=earnings_data,
        notifications=notifications
    )

@service_provider_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # Check if ServiceProvider already exists for current user
    provider = ServiceProvider.query.filter_by(user_id=current_user.id).first()

    # If not, create a new ServiceProvider record safely
    if not provider:
        provider = ServiceProvider(
            user_id=current_user.id,
            name=current_user.name or "Unnamed Provider",
            phone=current_user.phone_number or "Not provided",  # <-- fixed
            service="Not specified",                            # <-- required
            description="No description",                       # <-- required
            service_type="General Services",
            location="Not specified",
            available=True
        )
        db.session.add(provider)
        db.session.commit()

    # Handle form submission
    if request.method == 'POST':
        # Update profile information safely
        provider.name = request.form.get('name') or provider.name
        provider.phone = request.form.get('phone') or provider.phone          # <-- fixed to match form
        provider.service = request.form.get('services') or provider.service
        provider.description = request.form.get('description') or provider.description
        provider.service_type = request.form.get('service_type') or provider.service_type
        provider.location = request.form.get('location') or provider.location
        provider.available = 'available' in request.form
        provider.working_hours = request.form.get('working_hours') or provider.working_hours

        # Commit updates to the database
        try:
            db.session.commit()
            flash("Profile updated successfully.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}", "error")

        return redirect(url_for('service_provider.profile'))

    # Render profile template
    return render_template(
        'service_provider/profile.html',
        provider=provider,
        current_user=current_user
    )

@service_provider_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Verify current password
    if not check_password_hash(current_user.password_hash, current_password):
        flash('Current password is incorrect', 'danger')
        return redirect(url_for('service_provider.profile'))
    
    # Verify new passwords match
    if new_password != confirm_password:
        flash('New passwords do not match', 'danger')
        return redirect(url_for('service_provider.profile'))
    
    # Update password
    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    flash('Password updated successfully!', 'success')
    return redirect(url_for('service_provider.profile'))

@service_provider_bp.route('/toggle_availability', methods=['POST'])
@login_required
def toggle_availability():
    data = request.get_json()
    available = data.get('available', False)
    
    provider = ServiceProvider.query.filter_by(user_id=current_user.id).first()
    if provider:
        provider.available = available
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 400

@service_provider_bp.route('/earnings_data')
@login_required
def earnings_data():
    period = request.args.get('period', 'month')
    provider = ServiceProvider.query.filter_by(user_id=current_user.id).first()
    
    if not provider:
        return jsonify({'labels': [], 'values': []})
    
    labels = []
    values = []
    
    if period == 'week':
        # Get data for the last 7 days
        for i in range(7, 0, -1):
            date = datetime.now() - timedelta(days=i)
            labels.append(date.strftime('%a'))
            
            daily_earnings = db.session.query(
                func.sum(ServiceRequest.amount)
            ).filter(
                ServiceRequest.service_provider_id == provider.id,
                ServiceRequest.status == 'completed',
                func.date(ServiceRequest.completed_at) == date.date()
            ).scalar() or 0
            
            values.append(float(daily_earnings))
    
    elif period == 'month':
        # Get data for the last 30 days
        for i in range(30, 0, -1):
            date = datetime.now() - timedelta(days=i)
            labels.append(date.strftime('%b %d'))
            
            daily_earnings = db.session.query(
                func.sum(ServiceRequest.amount)
            ).filter(
                ServiceRequest.service_provider_id == provider.id,
                ServiceRequest.status == 'completed',
                func.date(ServiceRequest.completed_at) == date.date()
            ).scalar() or 0
            
            values.append(float(daily_earnings))
    
    elif period == 'year':
        # Get data for the last 12 months
        for i in range(12, 0, -1):
            date = datetime.now() - timedelta(days=30*i)
            labels.append(date.strftime('%b %Y'))
            
            monthly_earnings = db.session.query(
                func.sum(ServiceRequest.amount)
            ).filter(
                ServiceRequest.service_provider_id == provider.id,
                ServiceRequest.status == 'completed',
                extract('month', ServiceRequest.completed_at) == date.month,
                extract('year', ServiceRequest.completed_at) == date.year
            ).scalar() or 0
            
            values.append(float(monthly_earnings))
    
    return jsonify({'labels': labels, 'values': values})

# Additional routes for other dashboard pages would go here
@service_provider_bp.route('/requests')
@login_required
def requests():
    # Implementation for service requests page
    return render_template('service_provider_requests.html')

@service_provider_bp.route('/schedule')
@login_required
def schedule():
    # Implementation for schedule page
    return render_template('service_provider_schedule.html')

@service_provider_bp.route('/earnings')
@login_required
def earnings():
    # Implementation for earnings page
    return render_template('service_provider_earnings.html')

@service_provider_bp.route('/reviews')
@login_required
def reviews():
    # Implementation for reviews page
    return render_template('service_provider_reviews.html')

@service_provider_bp.route('/settings')
@login_required
def settings():
    # Implementation for settings page
    return render_template('service_provider_settings.html')