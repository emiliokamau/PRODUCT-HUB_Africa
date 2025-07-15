from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from models.models import Booking, Message, House, User
from extensions import db
#from app import db

tenant_bp = Blueprint('tenant', __name__, url_prefix='/tenant')

@tenant_bp.route('/dashboard')
@login_required
def dashboard():
    bookings = Booking.query.filter_by(tenant_id=current_user.id).all()
    return render_template('tenant.html', bookings=bookings)

@tenant_bp.route('/book/<int:house_id>')
@login_required
def book(house_id):
    booking = Booking(tenant_id=current_user.id, house_id=house_id, status='pending')
    db.session.add(booking)
    db.session.commit()
    return redirect(url_for('tenant.dashboard'))

@tenant_bp.route('/chat/<int:landlord_id>', methods=['GET', 'POST'])
@login_required
def chat(landlord_id):
    if request.method == 'POST':
        message = Message(sender_id=current_user.id, receiver_id=landlord_id, content=request.form['message'])
        db.session.add(message)
        db.session.commit()
    messages = Message.query.filter(
        ((Message.sender_id==current_user.id) & (Message.receiver_id==landlord_id)) |
        ((Message.sender_id==landlord_id) & (Message.receiver_id==current_user.id))
    ).order_by(Message.timestamp.asc()).all()
    landlord = User.query.get(landlord_id)
    return render_template('chat.html', messages=messages, user=landlord)