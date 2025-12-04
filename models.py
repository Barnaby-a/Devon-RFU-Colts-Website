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
    # account type: 'regular' | 'player' | 'coach'
    account_type = db.Column(db.String(50), nullable=False, default='regular')
    # optional club code (references Club.code)
    club_code = db.Column(db.String(64), nullable=True)

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
        # legacy method: store human-friendly club name
        self.club = club

    def set_club_code(self, code):
        # store club code (short identifier) if present
        self.club_code = code


class Club(db.Model):
    __tablename__ = 'club'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(64), unique=True, nullable=False)

    def __repr__(self):
        return f"<Club {self.name} ({self.code})>"
    
