from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.models import House

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/index')
def index():
    houses = House.query.all()
    return render_template('index.html', houses=houses)

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/contact')
def contact():
    return render_template('contact.html')

@main_bp.route('/terms')
def terms():
    return render_template('terms.html')

@main_bp.route('/privacy')
def privacy():
    return render_template('privacy.html')

@main_bp.route('/accessibility')
def accessibility():
    return render_template('accessibility.html')

@main_bp.route('/subscribe')
def subscribe():
    return render_template('subscribe.html')

@main_bp.route('/help')
def help():
    return render_template('help.html')


@main_bp.route('/subscribe', methods=['POST'])
def subscribe_post():
    email = request.form.get('email')
    if email:
        flash(f'Subscribed successfully with {email}', 'success')
    else:
        flash('No email provided', 'danger')
    return redirect(url_for('main.index'))