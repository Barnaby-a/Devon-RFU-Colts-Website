from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    access_level = db.Column(db.String(50), default='user')  # e.g., 'user', 'admin'
    name = db.Column(db.String(150), nullable=False)
    created_by = db.Column(db.String, nullable=False)
    club = db.Column(db.String(150), nullable=False)

    def set_access_level(self, level):
        self.access_level = level

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def set_name(self, name):
        self.name = name

    def set_created_by(self, creator):
        self.created_by = creator

    def set_club(self, club):
        self.club = club
    
