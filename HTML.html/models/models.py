from extensions import db  # ✅ import db from extensions, not from app
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))  # tenant, landlord, admin, service
    houses = db.relationship('House', backref='owner', lazy=True)

class House(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    image_urls = db.Column(db.Text)
    location = db.Column(db.String(255))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    available = db.Column(db.Boolean, default=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'))
    status = db.Column(db.String(50))

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


# from app import db
# from flask_login import UserMixin

# class User(db.Model, UserMixin):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     email = db.Column(db.String(100), unique=True)
#     password = db.Column(db.String(200))
#     role = db.Column(db.String(20))  # tenant, landlord, admin, service
#     houses = db.relationship('House', backref='owner', lazy=True)

# class House(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(200))
#     description = db.Column(db.Text)
#     category = db.Column(db.String(50))
#     image_urls = db.Column(db.Text)
#     location = db.Column(db.String(255))
#     lat = db.Column(db.Float)
#     lng = db.Column(db.Float)
#     available = db.Column(db.Boolean, default=True)
#     owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# class Booking(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'))
#     house_id = db.Column(db.Integer, db.ForeignKey('house.id'))
#     status = db.Column(db.String(50))

# class Message(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
#     receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
#     content = db.Column(db.Text)
#     timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# class ServiceProvider(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     service = db.Column(db.String(200))
#     phone = db.Column(db.String(20))
#     description = db.Column(db.Text)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
# ''' 