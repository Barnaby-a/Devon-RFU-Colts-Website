from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Extension instances used across the app to avoid circular imports
db = SQLAlchemy()
login_manager = LoginManager()
