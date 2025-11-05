from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='tenant')
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32), nullable=True)
    mpesa_details = db.Column(db.String(50), nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True)
    language = db.Column(db.String(10), default='en')

    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    profile_picture = db.Column(db.String(255))

    # Relationships
    houses = db.relationship('House', backref='owner', lazy=True)
    sent_messages = db.relationship(
        'Message',
        foreign_keys='Message.sender_id',
        backref='sender',
        lazy=True
    )
    received_messages = db.relationship(
        'Message',
        foreign_keys='Message.receiver_id',
        backref='receiver',
        lazy=True
    )
    payments = db.relationship('Payment', backref='tenant', lazy=True)
    maintenance_requests = db.relationship('MaintenanceRequest', backref='tenant', lazy=True)
    notifications = db.relationship('Notification', backref='tenant', lazy=True)
    events = db.relationship('Event', backref='tenant', lazy=True)

    # Chat relationships
    sent_chat_messages = db.relationship(
        'ChatMessage',
        foreign_keys='ChatMessage.user_id',
        back_populates='user',
        lazy=True,
        cascade="all, delete-orphan"
    )
    received_chat_messages = db.relationship(
        'ChatMessage',
        foreign_keys='ChatMessage.support_agent_id',
        back_populates='agent',
        lazy=True,
        cascade="all, delete-orphan"
    )

    # Support tickets
    support_tickets = db.relationship('SupportTicket', back_populates='user', lazy=True)

    # Password utils
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class House(db.Model):
    __tablename__ = "house"

    id = db.Column(db.Integer, primary_key=True)

    # Basic info
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    property_type = db.Column(db.String(50), nullable=False)

    # Multiple image paths stored as comma-separated string
    image_urls = db.Column(db.Text, nullable=False, default='/static/images/default-house.jpg')

    location = db.Column(db.String(255), nullable=False)
    available = db.Column(db.Boolean, default=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Address
    address_line1 = db.Column(db.String(255), nullable=False)
    address_line2 = db.Column(db.String(255), nullable=True)  # Optional
    city = db.Column(db.String(100), nullable=False)
    state_province = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False)

    # Property details
    rent_amount = db.Column(db.Float, nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False)
    bathrooms = db.Column(db.Float, nullable=False)
    size = db.Column(db.String(50), nullable=False)
    lease_term = db.Column(db.String(50), nullable=False)
    availability_date = db.Column(db.Date, nullable=False, default=date.today)

    # Features
    utilities = db.Column(db.Text, nullable=False)
    pets_allowed = db.Column(db.String(10), nullable=False)
    pet_restrictions = db.Column(db.String(255), nullable=True)  # Optional
    parking_availability = db.Column(db.String(50), nullable=False)
    furnished_status = db.Column(db.String(50), nullable=False)
    amenities = db.Column(db.Text, nullable=False)
    security_deposit = db.Column(db.Float, nullable=False)
    smoking_policy = db.Column(db.String(50), nullable=False)
    accessibility_features = db.Column(db.Text, nullable=True)  # Optional

    def get_image_list(self):
        """Return a list of image URLs from the comma-separated string."""
        return self.image_urls.split(',') if self.image_urls else []
    

# models.py

class PaymentMethods(db.Model):
    __tablename__ = 'payment_methods'
    
    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), nullable=False)
    
    # M-Pesa Till Number
    mpesa_till_number = db.Column(db.String(10))
    mpesa_business_name = db.Column(db.String(100))
    mpesa_enabled = db.Column(db.Boolean, default=False)
    
    # Paybill Number``
    paybill_number = db.Column(db.String(10))
    paybill_account_number = db.Column(db.String(50))
    paybill_enabled = db.Column(db.Boolean, default=False)
    
    # Bank Transfer
    bank_name = db.Column(db.String(100))
    bank_branch = db.Column(db.String(100))
    account_name = db.Column(db.String(100))
    account_number = db.Column(db.String(50))
    bank_enabled = db.Column(db.Boolean, default=False)
    
    # M-Pesa Send Money
    send_money_phone = db.Column(db.String(20))
    send_money_name = db.Column(db.String(100))
    send_money_enabled = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<PaymentMethods {self.id}>'
    

class PaymentTransaction(db.Model):
    __tablename__ = "payment_transactions"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), nullable=False)
    phone_number = db.Column(db.String(20))
    amount = db.Column(db.Float)
    mpesa_receipt = db.Column(db.String(100))
    result_code = db.Column(db.String(10))
    status = db.Column(db.String(20), default="Pending")  # Pending, Success, Failed
    transaction_time = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PaymentTransaction {self.mpesa_receipt}>"


    
class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)

    # ✅ FIX: Only one FK linking to User table
    tenant_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    tenant = db.relationship("User", backref="bookings")

    house_id = db.Column(db.Integer, db.ForeignKey("house.id"), nullable=False)

    house = db.relationship("House", backref="bookings", lazy=True)

    move_in_date = db.Column(db.Date, nullable=False)
    stay_duration = db.Column(db.String(50))
    special_requests = db.Column(db.Text)
    status = db.Column(db.String(50), default="Pending")
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    current_address = db.Column(db.String(255))

    lease_start_date = db.Column(db.Date)
    lease_term = db.Column(db.String(20))
    occupants_count = db.Column(db.Integer)
    pets = db.Column(db.String(10))

    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(50))
    emergency_contact_relationship = db.Column(db.String(100))

    deposit_paid = db.Column(db.Boolean, default=False)

    payment_method = db.Column(db.String(50))
    agree_terms = db.Column(db.Boolean, default=False)
    payment_status = db.Column(db.String(20), default="Pending")  # Pending, Paid, Failed




    

class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_provider_id = db.Column(db.Integer, db.ForeignKey('service_provider.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='Pending')
    amount = db.Column(db.Numeric(10, 2), nullable=True) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    date = db.Column(db.DateTime, nullable=False)  
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)

    tenant = db.relationship('User', foreign_keys=[tenant_id])
    service_provider = db.relationship('ServiceProvider', foreign_keys=[service_provider_id])




class Appointment(db.Model):
    __tablename__ = 'appointment'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_provider_id = db.Column(db.Integer, db.ForeignKey('service_provider.id'), nullable=False)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default="Scheduled")
    notes = db.Column(db.Text)

    tenant = db.relationship('User', backref='appointments')
    service_provider = db.relationship('ServiceProvider', backref='appointments')


class Review(db.Model):
    __tablename__ = 'review'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_provider_id = db.Column(db.Integer, db.ForeignKey('service_provider.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tenant = db.relationship('User', backref='reviews')
    service_provider = db.relationship('ServiceProvider', backref='reviews')


lease_start_date = db.Column(db.Date, nullable=False)
lease_term = db.Column(db.String(50), nullable=False)

occupants_count = db.Column(db.Integer, nullable=False)
pets = db.Column(db.String(10), nullable=True)

emergency_contact_name = db.Column(db.String(100), nullable=False)
emergency_contact_phone = db.Column(db.String(50), nullable=False)
emergency_contact_relationship = db.Column(db.String(50), nullable=False)

payment_method = db.Column(db.String(50), nullable=False)
first_name = db.Column(db.String(100), nullable=False)
last_name = db.Column(db.String(100), nullable=False)
email = db.Column(db.String(100), nullable=False)
phone = db.Column(db.String(50), nullable=False)
current_address = db.Column(db.String(255), nullable=False)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())


class ServiceProvider(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    service = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    description = db.Column(db.Text)
    service_type = db.Column(db.String(100))
    location = db.Column(db.String(255), default="Not specified")
    available = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='Pending')


class MaintenanceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'))  # 🏡 link to house
    issue = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='Open')
    date_submitted = db.Column(db.DateTime, default=db.func.current_timestamp())

    house = db.relationship('House', backref='maintenance_requests')


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=db.func.current_timestamp())


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)


# ----------------- ChatMessage -----------------
class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    support_agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_read = db.Column(db.Boolean, default=False)

    # Relationships (use back_populates to avoid conflicts)
    user = db.relationship('User', foreign_keys=[user_id], back_populates='sent_chat_messages')
    agent = db.relationship('User', foreign_keys=[support_agent_id], back_populates='received_chat_messages')

class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'))
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    tenant = db.relationship('User', backref='receipts')
    payment = db.relationship('Payment', backref='receipt')



# ----------------- SupportTicket -----------------
class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='open')  # open, resolved, escalated
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    # Relationship
    user = db.relationship('User', back_populates='support_tickets')
