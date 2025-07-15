from flask import Blueprint, render_template
from models.models import House

house_bp = Blueprint('house', __name__, url_prefix='/houses')

@house_bp.route('/rentals')
def rentals():
    houses = House.query.filter_by(category='Rental').all()
    return render_template('rentals.html', houses=houses)

@house_bp.route('/hotels')
def hotels():
    houses = House.query.filter_by(category='Hotel').all()
    return render_template('hotel.html', houses=houses)

@house_bp.route('/bnb')
def bnb():
    houses = House.query.filter_by(category='BNB').all()
    return render_template('bnb.html', houses=houses)

@house_bp.route('/real_estates')
def real_estates():
    houses = House.query.filter_by(category='RealEstate').all()
    return render_template('real_estates.html', houses=houses)


# from flask import current_app
# print("Using app:", current_app.name)
