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

from models import User

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
    return render_template("overview.html")

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
def dashboard():
    return render_template("dashboard.html")

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
            return redirect(url_for("dashboard"))
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


