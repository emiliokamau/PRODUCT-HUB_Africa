from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from models.models import House
from extensions import db  
from flask import current_app

#from app import db, app

landlord_bp = Blueprint('Landlord', __name__, url_prefix='/landlord')

# @landlord_bp.route('/')
# @login_required
# def dashboard():
#     return render_template('landlord.html')

UPLOAD_FOLDER = 'static/images'
#upload_folder = current_app.config['UPLOAD_FOLDER']
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

#app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#  Dashboard/Homepage after login
@landlord_bp.route('/')
@login_required
def dashboard():
    houses = House.query.filter_by(owner_id=current_user.id).all()
    return render_template('landlord.html', houses=houses)

@landlord_bp.route('/add_property', methods=['GET', 'POST'])
@login_required
def add_property():
    if request.method == 'POST':
        image_urls = []
        for file in request.files.getlist('images'):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
               # filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_urls.append('/' + filepath)

        house = House(
            title=request.form['title'],
            description=request.form['description'],
            category=request.form['category'],
            image_urls=','.join(image_urls),
            location=request.form['location'],
            lat=float(request.form['lat']),
            lng=float(request.form['lng']),
            owner_id=current_user.id
        )
        db.session.add(house)
        db.session.commit()
        flash('House uploaded successfully')
        return redirect(url_for('Landlord.dashboard'))
    return render_template('dashboard.html')

import os
from werkzeug.utils import secure_filename

@landlord_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        files = request.files.getlist('photos')
        image_paths = []
        for file in files:
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                #file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_paths.append(f"/static/images/{filename}")
        # Store image_paths in DB linked to the property
        return redirect(url_for('Landlord.upload'))
    return render_template('upload.html')
