# app.py
from flask import Flask, redirect, url_for
from config import Config
from extensions import db, migrate, login_manager
from flask_socketio import SocketIO, send
from flask_cors import CORS
from models.models import User



#from flask import Flask
#from config import Config
#from extensions import db, migrate, login_manager
#from flask_socketio import SocketIO
#from flask_cors import CORS
  # ✅ import from extensions

# the libraries are already installed in line 6
from flask_sqlalchemy import SQLAlchemy
from extensions import db 
#from flask_migrate import Migrate
#from flask_login import LoginManager
import os
 #from dotenv import load_dotenv
 #load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

app.config['UPLOAD_FOLDER'] = 'static/images'
print("Final DB URI =", app.config['SQLALCHEMY_DATABASE_URI'])

#load_dotenv()

# Extensions setup
#db = SQLAlchemy()
db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
#login_manager.login_view = 'login.html'

# after login_manager.init_app(app)
from models.models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

@socketio.on('message')
def handle_message(msg):
    print(f"Message received: {msg}")
    send(msg, broadcast=True)

# Blueprints
from routes.auth_routes import auth_bp
from routes.landlord_routes import landlord_bp
from routes.tenant_routes import tenant_bp
from routes.admin_routes import admin_bp
from routes.service_routes import service_bp
from routes.house_routes import house_bp

app.register_blueprint(auth_bp)
app.register_blueprint(landlord_bp)
app.register_blueprint(tenant_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(service_bp)
app.register_blueprint(house_bp)


from flask import redirect, url_for  # make sure this is imported

@app.route('/')
def root():
    return redirect(url_for('auth.signup'))


if __name__ == '__main__':
    socketio.run(app, debug=True)

#print("Loaded DB URI:", app.config['DATABASE_URI'])  ❌
#print("Loaded DB URI:", app.config['SQLALCHEMY_DATABASE_URI'])

# from flask import Flask
# from flask_sqlalchemy import SQLAlchemy
# from flask_migrate import Migrate
# from flask_login import LoginManager
# from flask_socketio import SocketIO, send
# from flask_cors import CORS
# from config import Config

# # Create app instance ONCE
# app = Flask(__name__)
# app.config.from_object(Config)

# print("Connecting to DB at:", app.config['SQLALCHEMY_DATABASE_URI'])

# from config import Config
# print("Loaded DB URI:", Config.SQLALCHEMY_DATABASE_URI)

# # Initialize extensions
# socketio = SocketIO(app, cors_allowed_origins="*")
# CORS(app)
# db = SQLAlchemy(app)
# migrate = Migrate(app, db)
# login_manager = LoginManager(app)
# login_manager.login_view = 'login'

# # Register SocketIO message event
# @socketio.on('message')
# def handle_message(msg):
#     print(f"Message received: {msg}")
#     send(msg, broadcast=True)

# # Register Blueprints
# from routes.auth_routes import auth_bp
# from routes.landlord_routes import landlord_bp
# from routes.tenant_routes import tenant_bp
# from routes.admin_routes import admin_bp
# from routes.service_routes import service_bp
# from routes.house_routes import house_bp

# app.register_blueprint(auth_bp)
# app.register_blueprint(landlord_bp)
# app.register_blueprint(tenant_bp)
# app.register_blueprint(admin_bp)
# app.register_blueprint(service_bp)
# app.register_blueprint(house_bp)

# # Run app
# if __name__ == '__main__':
#     socketio.run(app, debug=True)
