from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from models.models import ServiceProvider
from extensions import db
#from app import db

service_bp = Blueprint('service', __name__, url_prefix='/services')

@service_bp.route('/')
def service_list():
    services = ServiceProvider.query.all()
    return render_template('serviceprovider.html', services=services)

@service_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_service():
    if request.method == 'POST':
        service = ServiceProvider(
            name=request.form['name'],
            service=request.form['service'],
            phone=request.form['phone'],
            description=request.form['description'],
            user_id=current_user.id
        )
        db.session.add(service)
        db.session.commit()
        return redirect(url_for('service.service_list'))
    return render_template('add_service.html')