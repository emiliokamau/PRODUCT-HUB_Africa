from flask import Blueprint, render_template
from flask_login import login_required
from models.models import User, House

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    users = User.query.all()
    houses = House.query.all()
    return render_template('admin.html', users=users, houses=houses)


# from flask import current_app
# print("Using app:", current_app.name)
