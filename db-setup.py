from app import db, app

# Create all database tables
with app.app_context():
    db.drop_all()
    db.create_all()