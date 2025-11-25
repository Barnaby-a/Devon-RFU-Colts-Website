###############################
# DEVON RFU COLTS - Flask App #
###############################

# Import necessary libraries
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import logout_user, current_user, login_required, login_user, LoginManager
from flask_sqlalchemy import SQLAlchemy
#from decorators import access_level_required


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"  # simple file DB [web:28]
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "change-this-secret-key"

db = SQLAlchemy(app)
from models import User
login_manager = LoginManager()
login_manager.init_app(app)
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

# Defining the Sign Up page route
@app.route("/sign-up")
def sign_up():
    return render_template("sign-up.html")

@app.route("/login", methods=["GET", "POST"])
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


# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)


