from app import app
from extensions import db

# Create all database tables
with app.app_context():
    db.drop_all()
    db.create_all()