###############################
# DEVON RFU COLTS - Flask App #
###############################

# Import necessary libraries
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import logout_user, current_user, login_required, login_user
from extensions import db, login_manager
#from decorators import access_level_required


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"  # simple file DB [web:28]
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "change-this-secret-key"

# Initialize extensions with the app
db.init_app(app)
login_manager.init_app(app)
# Ensure Flask-Login redirects unauthenticated users to our login page
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from models import User
import os

# sponsor image extensions we'll accept
SPONSOR_EXTS = {'.svg', '.png', '.jpg', '.jpeg', '.webp', '.gif'}
from urllib.parse import urlparse


def _is_admin(user):
    """Return True if a user should be considered admin.

    Accepts numeric strings ("2") or integers >=2, or the literal string 'admin'.
    """
    if not user:
        return False
    level = getattr(user, 'access_level', None)
    if level is None:
        return False
    try:
        return int(level) >= 2
    except Exception:
        return str(level).lower() == 'admin'


def _is_safe_redirect(target):
    """Simple safety check for a redirect 'next' value: allow only same-site paths.

    This prevents open-redirects by rejecting absolute URLs.
    """
    if not target:
        return False
    parsed = urlparse(target)
    return (parsed.scheme == '' and parsed.netloc == '')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
 

# Defining the Home page route
@app.route("/")
def home():
    return render_template("home.html")

# Defining the Overview page route
@app.route("/overview")
def overview():
    # collect sponsor files from static/sponsors (if present)
    sponsors_dir = os.path.join(app.root_path, 'static', 'sponsors')
    sponsor_files = []
    try:
        for fn in sorted(os.listdir(sponsors_dir)):
            # ignore hidden files and directories; include any regular file so names/extensions don't matter
            if fn.startswith('.'):
                continue
            full = os.path.join(sponsors_dir, fn)
            if os.path.isfile(full):
                sponsor_files.append(fn)
    except Exception:
        sponsor_files = []

    return render_template("overview.html", sponsor_files=sponsor_files)

# Defining the Leaderboards page route
@app.route("/leaderboards")
def leaderboards():
    return render_template("leaderboards.html")

# Defining the Fixtures & Results page route
@app.route("/fixtures-results")
def fixtures_results():
    return render_template("fixtures_results.html")

# Defining the Stats centre page route
@app.route("/stats-centre")
def stats_centre():
    return render_template("stats_centre.html")

# Defining the Tables page route
@app.route("/tables")
def tables():
    return render_template("tables.html")

# Defining the News page route
@app.route("/news")
def news():
    return render_template("news.html")

# Defining the Dashboard page route
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route('/admin')
@login_required
def admin_dashboard():
    if not _is_admin(current_user):
        flash('You do not have access to the admin area.', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('dashboard_admin.html')

# Defining the Sign Up page route (GET shows form, POST creates user)
@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        name = request.form.get("name") or ""
        club = request.form.get("club") or ""

        # Basic validation
        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("signup.html")

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("An account with that email already exists.", "danger")
            return render_template("signup.html")

        # Create user
        user = User(email=email)
        user.set_password(password)
        user.set_name(name if name else email)
        user.set_club(club if club else "")
        user.set_created_by("self")

        # Persist
        with app.app_context():
            db.session.add(user)
            db.session.commit()

        flash("Account created — you can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/log-in", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        remember = request.form.get("remember") == "on"
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash("Logged in successfully.", "success")
            # Respect 'next' parameter but only if it's a safe local URL
            next_url = request.args.get('next') or request.form.get('next')
            if next_url and _is_safe_redirect(next_url):
                return redirect(next_url)
            # Admin users go to admin dashboard by default
            if _is_admin(user):
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route('/logout')
def logout():
    try:
        logout_user()
    except Exception:
        pass
    flash('You have been signed out.', 'info')
    return redirect(url_for('home'))


# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)


