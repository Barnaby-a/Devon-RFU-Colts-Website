from app import app
from extensions import db
from models import User

with app.app_context():
    existing = User.query.filter_by(email="admin@example.com").first()
    if existing:
        # update existing record to ensure superadmin privileges
        existing.set_password("AdminPass123")
        existing.set_access_level('superadmin')
        existing.set_name("Admin User")
        existing.set_created_by("system")
        existing.set_club("N/A")
        db.session.commit()
        print("Updated existing superadmin: admin@example.com")
    else:
        admin = User(email="admin@example.com")
        admin.set_password("AdminPass123")
        admin.set_access_level('superadmin')
        admin.set_name("Admin User")
        admin.set_created_by("system")
        admin.set_club("N/A")
        db.session.add(admin)
        db.session.commit()
        print("Created superadmin: admin@example.com")