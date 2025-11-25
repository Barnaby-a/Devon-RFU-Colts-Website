from app import db, app
from models import User

admin = User(email="admin@example.com")
admin.set_password("AdminPass123")
admin.set_access_level(2)
admin.set_name("Admin User")
admin.set_created_by("system")
admin.set_club("N/A")

with app.app_context():
    db.session.add(admin)
    db.session.commit()