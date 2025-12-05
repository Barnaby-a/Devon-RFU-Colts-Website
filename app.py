###############################
# DEVON RFU COLTS - Flask App #
###############################

# Import necessary libraries
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import logout_user, current_user, login_required, login_user
from extensions import db, login_manager
#from decorators import access_level_required

#setup
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db" 
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "change-this-secret-key"

# Initialize extensions with the app
db.init_app(app)
login_manager.init_app(app)
# Ensure Flask-Login redirects unauthenticated users to our login page
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from models import User, Team, Match
from datetime import datetime
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
    # fetch the next upcoming match (UTC) to show on the home page
    now = datetime.utcnow()
    try:
        next_match = Match.query.filter(Match.date_time >= now).order_by(Match.date_time.asc()).first()
        # last 3 completed results (most recent first)
        last_results = Match.query.filter(
            Match.home_score != None,
            Match.away_score != None,
            Match.date_time < now
        ).order_by(Match.date_time.desc()).limit(3).all()
    except Exception:
        next_match = None
        last_results = []
    return render_template("home.html", next_match=next_match, last_results=last_results, now=now)

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
    # load matches and split into upcoming and past
    now = datetime.utcnow()
    try:
        upcoming = Match.query.filter(Match.date_time >= now).order_by(Match.date_time.asc()).all()
        past = Match.query.filter(Match.date_time < now).order_by(Match.date_time.desc()).all()
    except Exception:
        upcoming = []
        past = []

    return render_template("fixtures_results.html", upcoming=upcoming, past=past, now=now)

# Defining the Stats centre page route
@app.route("/stats-centre")
def stats_centre():
    return render_template("stats_centre.html")

# Defining the Tables page route (show non-sensitive DB tables to admins)
@app.route("/tables")
@login_required
def tables():
    if not _is_admin(current_user):
        flash('You do not have access to view database tables.', 'danger')
        return redirect(url_for('dashboard'))
    try:
        matches = Match.query.order_by(Match.date_time.desc()).all()
    except Exception:
        matches = []
    return render_template("tables.html", matches=matches)

# Defining the News page route
@app.route("/news")
def news():
    return render_template("news.html")


# Legal / policy pages
@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')


@app.route('/cookie-policy')
def cookie_policy():
    return render_template('cookie_policy.html')

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
    # provide some quick counts for admin overview
    try:
        team_count = Team.query.count()
        match_count = Match.query.count()
        upcoming_count = Match.query.filter(Match.date_time >= datetime.utcnow()).count()
        past_count = Match.query.filter(Match.date_time < datetime.utcnow()).count()
    except Exception:
        team_count = match_count = upcoming_count = past_count = 0
    return render_template('dashboard_admin.html', team_count=team_count, match_count=match_count, upcoming_count=upcoming_count, past_count=past_count)


# Admin: list and manage matches
@app.route('/admin/matches')
@login_required
def admin_matches():
    if not _is_admin(current_user):
        flash('You do not have access to the admin area.', 'danger')
        return redirect(url_for('dashboard'))
    # show all matches
    matches = Match.query.order_by(Match.date_time.desc()).all()
    teams = Team.query.order_by(Team.name).all()
    return render_template('admin_matches.html', matches=matches, teams=teams)


@app.route('/admin/teams')
@login_required
def admin_teams():
    if not _is_admin(current_user):
        flash('You do not have access to the admin area.', 'danger')
        return redirect(url_for('dashboard'))
    teams = Team.query.order_by(Team.name).all()
    return render_template('admin_teams.html', teams=teams)


@app.route('/admin/team/new', methods=['GET', 'POST'])
@login_required
def admin_team_new():
    if not _is_admin(current_user):
        flash('You do not have access to the admin area.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        code = (request.form.get('code') or '').strip()
        logo = (request.form.get('logo_filename') or '').strip()
        if not name:
            flash('Team name is required.', 'danger')
            return render_template('admin_team_form.html', team=None)
        t = Team(name=name, code=code, logo_filename=logo)
        try:
            db.session.add(t)
            db.session.commit()
            flash('Team created.', 'success')
            return redirect(url_for('admin_teams'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating team: {e}', 'danger')
    return render_template('admin_team_form.html', team=None)


@app.route('/admin/team/<int:team_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_team_edit(team_id):
    if not _is_admin(current_user):
        flash('You do not have access to the admin area.', 'danger')
        return redirect(url_for('dashboard'))
    t = Team.query.get_or_404(team_id)
    if request.method == 'POST':
        t.name = (request.form.get('name') or '').strip()
        t.code = (request.form.get('code') or '').strip()
        t.logo_filename = (request.form.get('logo_filename') or '').strip()
        if not t.name:
            flash('Team name is required.', 'danger')
            return render_template('admin_team_form.html', team=t)
        try:
            db.session.commit()
            flash('Team updated.', 'success')
            return redirect(url_for('admin_teams'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating team: {e}', 'danger')
    return render_template('admin_team_form.html', team=t)


@app.route('/admin/team/<int:team_id>/delete', methods=['POST'])
@login_required
def admin_team_delete(team_id):
    if not _is_admin(current_user):
        flash('You do not have access to the admin area.', 'danger')
        return redirect(url_for('dashboard'))
    t = Team.query.get_or_404(team_id)
    try:
        db.session.delete(t)
        db.session.commit()
        flash('Team deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting team: {e}', 'danger')
    return redirect(url_for('admin_teams'))


@app.route('/admin/match/new', methods=['GET', 'POST'])
@login_required
def admin_match_new():
    if not _is_admin(current_user):
        flash('You do not have access to the admin area.', 'danger')
        return redirect(url_for('dashboard'))
    teams = Team.query.order_by(Team.name).all()
    if request.method == 'POST':
        try:
            home_team_id = int(request.form.get('home_team'))
            away_team_id = int(request.form.get('away_team'))
            dt_raw = request.form.get('date_time')
            # datetime-local comes in like '2025-12-05T14:30'
            date_time = datetime.fromisoformat(dt_raw) if dt_raw else datetime.utcnow()
            location = request.form.get('location') or ''
            m = Match(home_team_id=home_team_id, away_team_id=away_team_id, date_time=date_time, location=location)
            db.session.add(m)
            db.session.commit()
            flash('Match created.', 'success')
            return redirect(url_for('admin_matches'))
        except Exception as e:
            flash(f'Error creating match: {e}', 'danger')
    return render_template('admin_match_form.html', teams=teams, match=None)


@app.route('/admin/match/<int:match_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_match_edit(match_id):
    if not _is_admin(current_user):
        flash('You do not have access to the admin area.', 'danger')
        return redirect(url_for('dashboard'))
    m = Match.query.get_or_404(match_id)
    teams = Team.query.order_by(Team.name).all()
    if request.method == 'POST':
        try:
            m.home_team_id = int(request.form.get('home_team'))
            m.away_team_id = int(request.form.get('away_team'))
            dt_raw = request.form.get('date_time')
            m.date_time = datetime.fromisoformat(dt_raw) if dt_raw else m.date_time
            m.location = request.form.get('location') or ''
            # scores may be empty
            hs = request.form.get('home_score')
            ascore = request.form.get('away_score')
            m.home_score = int(hs) if hs not in (None, '', 'None') else None
            m.away_score = int(ascore) if ascore not in (None, '', 'None') else None
            db.session.commit()
            flash('Match updated.', 'success')
            return redirect(url_for('admin_matches'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating match: {e}', 'danger')
    return render_template('admin_match_form.html', teams=teams, match=m)

# Defining the Sign Up page route (GET shows form, POST creates user)
@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        name = request.form.get("name") or ""
        account_type = request.form.get("account_type") or 'regular'
        club_code = (request.form.get("club_code") or "").strip()

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
        user.account_type = account_type
        # Store any provided club_code as free-text (no DB validation)
        user.set_club("")
        user.set_club_code(club_code)
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


