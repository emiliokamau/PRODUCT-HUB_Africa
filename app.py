from flask import Flask, redirect, url_for, flash, render_template, request, jsonify, session, abort
from config import Config
from extensions import db, migrate, login_manager, csrf
from flask_socketio import SocketIO
from flask_cors import CORS
#from models.models import User, House, ChatMessage, SupportTicket, Booking, Payment
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from datetime import datetime, timedelta
import os
import logging
from flask_wtf import CSRFProtect, FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email
from flask import Blueprint
from flask import jsonify, session
from flask_login import current_user
#import uuid
#from dateutil.relativedelta import relativedelta



def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    
    
    #IMPORTS
    from flask_socketio import SocketIO, join_room, leave_room, emit
    from models.models import User, House, ChatMessage, SupportTicket, Booking, Payment, Message
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    import uuid
    #from models.models import MaintenanceRequest

    # SESSION TIMEOUT SETTINGS
    app.permanent_session_lifetime = timedelta(minutes=20)
    app.config['SESSION_PERMANENT'] = True

    # Ensure critical configurations
    app.config['SECRET_KEY'] = app.config.get('SECRET_KEY', 'your-secure-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///app.db')
    app.config['UPLOAD_FOLDER'] = app.config.get('UPLOAD_FOLDER', 'static/images')
    app.config['CHAT_UPLOAD_FOLDER'] = app.config.get('CHAT_UPLOAD_FOLDER', 'static/uploads/chat')
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    print("Final DB URI =", app.config['SQLALCHEMY_DATABASE_URI'])
    print("UPLOAD_FOLDER =", app.config['UPLOAD_FOLDER'])
    print("CHAT_UPLOAD_FOLDER =", app.config['CHAT_UPLOAD_FOLDER'])
    
    # Create chat upload directory
    os.makedirs(app.config['CHAT_UPLOAD_FOLDER'], exist_ok=True)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    socketio = SocketIO(app, cors_allowed_origins="*")
    CORS(app)

    # Subscribe form
    class SubscribeForm(FlaskForm):
        email = StringField('Email', validators=[DataRequired(), Email()])
        submit = SubmitField('Subscribe')

    # Exempt support_bp from CSRF (for SocketIO)
    csrf.exempt('routes.support_routes.support_bp')

    # Login manager
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            logger.error(f"Error loading user {user_id}: {str(e)}")
            return None

    # Refresh session
    @app.before_request
    def before_request():
        if current_user.is_authenticated:
            session.modified = True

    # Jinja filters
    def timeago(value):
        if not isinstance(value, datetime):
            return value
        lang = getattr(current_user, "language", "en") if current_user.is_authenticated else "en"
        now = datetime.utcnow()
        diff = now - value
        seconds = diff.total_seconds()
        minutes = divmod(seconds, 60)[0]
        hours = divmod(seconds, 3600)[0]
        days = divmod(seconds, 86400)[0]
        if lang == "sw":
            if seconds < 60:
                return "sasa hivi"
            elif minutes < 60:
                return f"dakika {int(minutes)} zilizopita"
            elif hours < 24:
                return f"masaa {int(hours)} yaliyopita"
            elif days == 1:
                return "jana"
            elif days < 7:
                return f"siku {int(days)} zilizopita"
            elif days < 30:
                return f"wiki {int(days // 7)} zilizopita"
            elif days < 365:
                return f"miezi {int(days // 30)} iliyopita"
            else:
                return f"miaka {int(days // 365)} iliyopita"
        else:
            if seconds < 60:
                return "just now"
            elif minutes < 60:
                return f"{int(minutes)} minute(s) ago"
            elif hours < 24:
                return f"{int(hours)} hour(s) ago"
            elif days == 1:
                return "yesterday"
            elif days < 7:
                return f"{int(days)} day(s) ago"
            elif days < 30:
                return f"{int(days // 7)} week(s) ago"
            elif days < 365:
                return f"{int(days // 30)} month(s) ago"
            else:
                return f"{int(days // 365)} year(s) ago"

    def datetimeformat(value, format="%Y-%m-%d %H:%M"):
        if not isinstance(value, datetime):
            return value
        return value.strftime(format)

    app.jinja_env.filters['timeago'] = timeago
    app.jinja_env.filters['datetimeformat'] = datetimeformat
    
    

    # Blueprints
    from routes.auth_routes import auth_bp
    from routes.landlord_routes import landlord_bp
    from routes.tenant_routes import tenant_bp
    from routes.admin_routes import admin_bp
    from routes.service_routes import service_provider_bp
    from routes.house_routes import house_bp
    from routes.main import main_bp
    from routes.support_routes import support_bp
    from routes.payments_routes import payments_bp
    csrf.exempt(payments_bp)
    from flask import send_from_directory

    # ------------------------------------------------------------------
    # REGISTER BLUEPRINTS (MUST BE BEFORE ADDING NEW ROUTES!)
    # ------------------------------------------------------------------
    app.register_blueprint(auth_bp)
    app.register_blueprint(landlord_bp)
    app.register_blueprint(tenant_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(service_provider_bp)
    app.register_blueprint(house_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(support_bp)
    app.register_blueprint(payments_bp)


    # ------------------------------------------------------------------
    # NEW: API BLUEPRINT FOR BOOKINGS
    # ------------------------------------------------------------------
    api_bp = Blueprint('api', __name__, url_prefix='/api')

    def booking_to_dict(booking):
        return {
            'id': booking.id,
            'tenant_name': booking.tenant.name,
            'tenant': {
                'profile_picture': booking.tenant.profile_picture
            },
            'house': {
                'title': booking.house.title,
                'rent_amount': booking.house.rent_amount
            },
            'move_in_date': booking.move_in_date.isoformat() if booking.move_in_date else None,
            'status': booking.status
        }

    @api_bp.route('/bookings', methods=['GET'])
    @login_required
    def api_list_bookings():
        search = request.args.get('search', '').strip()
        status = request.args.get('status')
        property_id = request.args.get('property')

        q = Booking.query.join(House).filter(House.landlord_id == current_user.id)

        if search:
            q = q.join(User).filter(
                or_(
                    User.name.ilike(f'%{search}%'),
                    House.title.ilike(f'%{search}%')
                )
            )
        if status and status != 'all':
            q = q.filter(Booking.status == status.title())
        if property_id and property_id != 'all':
            q = q.filter(Booking.house_id == int(property_id))

        bookings = q.all()
        return jsonify({'bookings': [booking_to_dict(b) for b in bookings]})

    @api_bp.route('/bookings/<int:booking_id>', methods=['GET'])
    @login_required
    def api_get_booking(booking_id):
        booking = Booking.query.get_or_404(booking_id)

        if booking.house.owner_id != current_user.id:
            return jsonify(success=False, message='Unauthorized'), 403

        return jsonify(success=True, booking=booking_to_dict(booking))


    @api_bp.route('/bookings/<int:booking_id>/approve', methods=['POST'])
    @login_required
    @csrf.exempt
    def api_approve_booking(booking_id):
        booking = Booking.query.get_or_404(booking_id)
        booking.status = 'Awaiting Deposit'
        booking.deposit_due_by = datetime.utcnow() + timedelta(days=2) # 48-hour deadline
        db.session.commit()
        return jsonify(success=True, message='Booking approved! Waiting for tenant deposit.')
    
    @api_bp.route('/bookings/<int:booking_id>/revoke', methods=['POST'])
    @login_required
    @csrf.exempt
    def api_revoke_booking(booking_id):
        booking = Booking.query.get_or_404(booking_id)

        if booking.house.owner_id != current_user.id:
            return jsonify(success=False, message='Unauthorized'), 403

    # CRITICAL: Landlord can ONLY revoke if deposit has not been paid
        if booking.status == 'Awaiting Deposit':
            booking.status = 'Revoked'
            db.session.commit()
            return jsonify(success=True, message='Booking approval revoked.')
        elif booking.status == 'Confirmed':
            return jsonify(success=False, message='Cannot revoke a confirmed booking (deposit paid).')
        else:
            return jsonify(success=False, message='Invalid booking state.')
    
    @api_bp.route('/bookings/<int:booking_id>/reject', methods=['POST'])
    @login_required
    @csrf.exempt
    def api_reject_booking(booking_id):
        booking = Booking.query.get_or_404(booking_id)

        if booking.house.owner_id != current_user.id:
            return jsonify(success=False, message='Unauthorized'), 403

        booking.status = 'Rejected'
        db.session.commit()
        return jsonify(success=True, message='Booking rejected successfully!')

    
    @csrf.exempt
    @api_bp.route('/pay/deposit/<int:booking_id>', methods=['POST'])
    @login_required
    def pay_deposit(booking_id):
        try:
            booking = Booking.query.get_or_404(booking_id)

            # Ensure tenant owns this booking
            if booking.tenant_id != current_user.id:
                return jsonify(success=False, message="Unauthorized"), 403

            # Check status
            if booking.status != 'Awaiting Deposit':
                return jsonify(success=False, message=f"Booking is not awaiting deposit. Status is: {booking.status}"), 400

            # Example validation (optional)
            # if booking.deposit_paid:
            #     return jsonify(success=False, message="Deposit already paid"), 400

            # Simulate MPESA payment success (for now)
            booking.deposit_paid = True
            booking.status = 'Confirmed'

            # 2. Set the first rent payment due date
            if booking.move_in_date:
            # Set it to 1 month from their move-in date
                booking.next_rent_payment_due = booking.move_in_date + relativedelta(months=1)
            else:
            # Fallback
                booking.next_rent_payment_due = datetime.utcnow() + relativedelta(months=1)

        # 3. Create the first Payment record (for the deposit)
            new_deposit_amount = booking.house.security_deposit + (booking.house.rent_amount / 2)
            deposit_payment = Payment(
                tenant_id=current_user.id,
                booking_id=booking.id,
                amount=new_deposit_amount,
                date=datetime.utcnow(),
                status='Paid',
                payment_for='Security Deposit',
                receipt_id=f"RCPT-{uuid.uuid4().hex[:10].upper()}"
            )

            db.session.add(deposit_payment)
            db.session.commit()

            return jsonify(success=True, message="Deposit paid successfully! Your booking is confirmed.")

        except Exception as e:
            db.session.rollback()
            # Always return JSON, even for errors
            print("Payment error:", e)
            return jsonify(success=False, message=f"Server error: {str(e)}"), 500






    app.register_blueprint(api_bp)


     # ------------------------------------------------------------------
    # NEW: SOCKET.IO LOGIC FOR PEER-TO-PEER (TENANT-LANDLORD) CHAT
    # ------------------------------------------------------------------
    
    # We use your 'socketio' variable, which is already initialized
    
    @socketio.on('join_peer_room')
    def handle_join_peer_room():
        """Called when a user opens a chat window."""
        if current_user.is_authenticated:
            # We create a private "room" for this user, using their ID.
            # Only they can receive messages sent to this room.
            join_room(current_user.id)
            print(f"User {current_user.id} joined their private peer room.")

    @socketio.on('leave_peer_room')
    def handle_leave_peer_room():
        """Called when a user closes a chat window."""
        if current_user.is_authenticated:
            leave_room(current_user.id)
            print(f"User {current_user.id} left their private peer room.")

    @socketio.on('send_peer_message')
    def handle_send_peer_message(data):
        """Called when a user sends a tenant-landlord message."""
        if not current_user.is_authenticated:
            return  # Ignore unauthenticated

        receiver_id = data.get('receiver_id')
        content = data.get('content')

        if not receiver_id or not content:
            return  # Ignore empty messages

        # Save the message to the database
        # Note: Your model might be 'ChatMessage', 
        # I've used 'Message' here based on tenant_routes.py
        # try:
        #     from models.models import Message # Import here
        # except ImportError:
        #     from models.models import ChatMessage as Message # Fallback
            
        message = Message(
            sender_id=current_user.id,
            receiver_id=int(receiver_id),
            content=content,
            timestamp=datetime.utcnow()
        )
        db.session.add(message)
        db.session.commit()

        # Create a payload to send
        message_payload = {
            'sender_id': message.sender_id,
            'receiver_id': message.receiver_id,
            'content': message.content,
            'timestamp': message.timestamp.isoformat()
        }

        # Emit the message to the sender (so they see their own message)
        emit('receive_peer_message', message_payload, room=current_user.id)
        
        # Emit the message to the recipient's private room
        emit('receive_peer_message', message_payload, room=int(receiver_id))
    # ------------------------------------------------------------------
    # EXISTING ROUTES
    # ------------------------------------------------------------------
#from flask import render_template, request, jsonify, redirect, url_for, flash
#from app import app, db
#from models import Property
#from flask_login import login_required, current_user
    @app.route('/')
    def root():
        logger.info("Redirecting to index page")
        return render_template('index.html')

    @app.route("/index")
    def index():
        try:
            houses = House.query.order_by(House.id.desc()).limit(12).all()
            return render_template("index.html", houses=houses)
        except Exception as e:
            logger.error(f"Error fetching houses: {str(e)}")
            flash("Error loading houses. Please try again.", "danger")
            return render_template("index.html", houses=[])
     
    

    @app.route('/property/<int:property_id>')
    def view_property(property_id):
        property = House.query.get_or_404(property_id)
        return render_template('property_detail.html', property=property)

    @app.route('/book_property/<int:property_id>')
    @login_required
    def book_property(property_id):
        property = House.query.get_or_404(property_id)
        # Implement booking logic here
        return redirect(url_for('view_property', property_id=property_id))

    # API endpoints for AJAX calls
    @app.route('/api/favorites', methods=['POST'])
    @login_required
    def add_to_favorites():
        property_id = request.json.get('property_id')
        # Implement adding to favorites logic here
        return jsonify({'success': True})

    @app.route('/api/favorites/<int:property_id>', methods=['DELETE'])
    @login_required
    def remove_from_favorites(property_id):
        # Implement removing from favorites logic here
        return jsonify({'success': True})
    # @app.route('/properties/<int:id>')
    # def properties(id):
    #     property = House.query.order_by(House.id.desc()).get(id).all()
    #     return render_template('properties.html', image_filename=property.image)
    
    @app.route('/uploads/properties/<filename>')
    def uploaded_file(filename):
        return send_from_directory(os.path.join(app.root_path, 'static/uploads/properties'), filename)

    

    @app.route("/subscribe", methods=["GET", "POST"])
    def subscribe():
        form = SubscribeForm()
        if form.validate_on_submit():
            email = form.email.data
            try:
                logger.info(f"Subscription attempt with email: {email}")
                flash(f"Subscribed successfully with {email}", "success")
                return redirect(url_for("index"))
            except Exception as e:
                logger.error(f"Error processing subscription: {str(e)}")
                flash("Error processing subscription.", "danger")
        return render_template("subscribe.html", form=form)

    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf())

    @app.route('/portal')
    @login_required
    def portal():
        role = current_user.role.lower()
        logger.info(f"User {current_user.id} accessing portal with role: {role}")
        if role == 'admin':
            return redirect(url_for('admin.manage_users'))
        elif role == 'landlord':
            return redirect(url_for('landlord.dashboard'))
        elif role == 'tenant':
            return redirect(url_for('tenant.dashboard'))
        elif role == 'service_provider':
            return redirect(url_for('service_provider_dashboard.dashboard'))
        else:
            logger.warning(f"Unrecognized role for user {current_user.id}: {role}")
            flash("Unrecognized role. Contact system administrator.", "danger")
            return redirect(url_for('auth.logout'))
        
    # ✅ Route to handle AJAX session refresh
    @csrf.exempt
    @app.route('/refresh-session', methods=['POST'])
    def refresh_session():
        if current_user.is_authenticated:
            session.modified = True
            return jsonify({"status": "ok"}), 200
        return jsonify({"status": "unauthorized"}), 401
    

    return app, socketio


# Create app and socketio
app, socketio = create_app()


# Run
if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.error(f"Error creating database tables: {str(e)}")
    socketio.run(app, debug=True, use_reloader=False)