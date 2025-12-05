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

from models import User, Team, Match, Player
from sqlalchemy import or_
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
    # keep backward-compatible numeric/admin checks, but prefer new role helpers when available
    try:
        if hasattr(user, 'is_superadmin'):
            return user.is_superadmin()
    except Exception:
        pass
    try:
        return int(level) >= 2
    except Exception:
        return str(level).lower() in ('admin', 'superadmin')


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
        q = request.args.get('q', '').strip()
        # base queries
        upcoming_q = Match.query.filter(Match.date_time >= now)
        past_q = Match.query.filter(Match.date_time < now)
        if q:
            # find matching team ids by name or code
            teams = Team.query.filter(or_(Team.name.ilike(f"%{q}%"), Team.code == q)).all()
            ids = [t.id for t in teams]
            if ids:
                upcoming_q = upcoming_q.filter((Match.home_team_id.in_(ids)) | (Match.away_team_id.in_(ids)))
                past_q = past_q.filter((Match.home_team_id.in_(ids)) | (Match.away_team_id.in_(ids)))
        upcoming = upcoming_q.order_by(Match.date_time.asc()).all()
        past = past_q.order_by(Match.date_time.desc()).all()
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
    # Player-specific dashboard: show upcoming matches for their team and teammates
    if current_user.is_player():
        profile = getattr(current_user, 'player_profile', None)
        if profile and profile.team_id:
            team = Team.query.get(profile.team_id)
            now = datetime.utcnow()
            upcoming = Match.query.filter(
                ((Match.home_team_id == team.id) | (Match.away_team_id == team.id)) & (Match.date_time >= now)
            ).order_by(Match.date_time.asc()).all()
            teammates = Player.query.filter_by(team_id=team.id).join(User).all()
            return render_template('dashboard_player.html', team=team, upcoming=upcoming, teammates=teammates)
        # fallback to regular dashboard if no player profile/team
        return render_template('dashboard.html')
    # If this user is an admin (including legacy numeric roles), send them to the admin dashboard
    if _is_admin(current_user):
        return redirect(url_for('admin_dashboard'))
    # For regular users, provide list of teams so they can follow clubs from dashboard
    teams = Team.query.order_by(Team.name).all()
    return render_template("dashboard.html", teams=teams)


# Superadmin: assign coaches to a team
@app.route('/admin/team/<int:team_id>/coaches', methods=['GET', 'POST'])
@login_required
def admin_team_coaches(team_id):
    if not current_user.is_superadmin():
        flash('Only superadmins may manage team coaches.', 'danger')
        return redirect(url_for('admin_teams'))
    t = Team.query.get_or_404(team_id)
    # list users who might be coaches (all users)
    users = User.query.order_by(User.name).all()
    if request.method == 'POST':
        try:
            user_id = int(request.form.get('user_id'))
            u = User.query.get_or_404(user_id)
            # set access level to coach and link
            u.access_level = 'coach'
            if u not in t.coaches:
                t.coaches.append(u)
            db.session.commit()
            flash('Coach assigned to team.', 'success')
            return redirect(url_for('admin_team_coaches', team_id=team_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error assigning coach: {e}', 'danger')
    return render_template('admin_team_coaches.html', team=t, users=users)


# Coach: manage players for a team (coaches can add players to teams they coach)
@app.route('/coach/team/<int:team_id>/players', methods=['GET', 'POST'])
@login_required
def coach_team_players(team_id):
    t = Team.query.get_or_404(team_id)
    # allow only coaches of this team or superadmins
    if not (current_user.is_superadmin() or (current_user.is_coach() and t in current_user.coached_teams)):
        flash('You do not have permission to manage players for this team.', 'danger')
        return redirect(url_for('dashboard'))
    # support search filtering for players
    q = request.args.get('q', '').strip()
    if q:
        players = Player.query.filter_by(team_id=team_id).join(User).filter(or_(User.name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%"))).all()
    else:
        players = Player.query.filter_by(team_id=team_id).all()
    if request.method == 'POST':
        # create a new player user and player profile
        email = (request.form.get('email') or '').strip()
        name = (request.form.get('name') or '').strip()
        password = (request.form.get('password') or '').strip()
        squad_number = (request.form.get('squad_number') or '').strip()
        position = (request.form.get('position') or '').strip()
        if not email or not password:
            flash('Email and password required to create player account.', 'danger')
            return render_template('coach_players.html', team=t, players=players)
        try:
            existing = User.query.filter_by(email=email).first()
            if existing:
                flash('A user with that email already exists.', 'danger')
                return render_template('coach_players.html', team=t, players=players)
            u = User(email=email, name=name if name else email, created_by=current_user.email, club='')
            u.set_password(password)
            u.access_level = 'player'
            db.session.add(u)
            db.session.commit()
            p = Player(user_id=u.id, team_id=team_id, squad_number=squad_number or None, position=position or None)
            db.session.add(p)
            db.session.commit()
            flash('Player account created and added to team.', 'success')
            return redirect(url_for('coach_team_players', team_id=team_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating player: {e}', 'danger')
    return render_template('coach_players.html', team=t, players=players)


@app.route('/coach/team/<int:team_id>/edit', methods=['GET', 'POST'])
@login_required
def coach_team_edit(team_id):
    t = Team.query.get_or_404(team_id)
    # allow only coaches of this team or superadmins
    if not (current_user.is_superadmin() or (current_user.is_coach() and t in current_user.coached_teams)):
        flash('You do not have permission to edit this team.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        t.name = (request.form.get('name') or t.name).strip()
        t.code = (request.form.get('code') or '').strip()
        t.logo_filename = (request.form.get('logo_filename') or t.logo_filename).strip()
        try:
            db.session.commit()
            flash('Team updated.', 'success')
            return redirect(url_for('coach_team_edit', team_id=team_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating team: {e}', 'danger')
    return render_template('coach_team_edit.html', team=t)


@app.route('/follow/team/<int:team_id>', methods=['POST'])
@login_required
def follow_team(team_id):
    t = Team.query.get_or_404(team_id)
    try:
        if t not in current_user.followed_teams:
            current_user.followed_teams.append(t)
            db.session.commit()
            flash(f'Now following {t.name}.', 'success')
    except Exception:
        db.session.rollback()
        flash('Unable to follow team.', 'danger')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/follow', methods=['POST'])
@login_required
def follow_from_form():
    team_id_raw = request.form.get('team_id')
    if not team_id_raw:
        flash('No team selected.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))
    try:
        team_id = int(team_id_raw)
    except Exception:
        flash('Invalid team selected.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))
    return follow_team(team_id)


@app.route('/unfollow/team/<int:team_id>', methods=['POST'])
@login_required
def unfollow_team(team_id):
    t = Team.query.get_or_404(team_id)
    try:
        if t in current_user.followed_teams:
            current_user.followed_teams.remove(t)
            db.session.commit()
            flash(f'Unfollowed {t.name}.', 'info')
    except Exception:
        db.session.rollback()
        flash('Unable to unfollow team.', 'danger')
    return redirect(request.referrer or url_for('dashboard'))


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
    # allow superadmins full access; allow coaches to view/edit matches for teams they coach
    if not (current_user.can_edit_matches() or current_user.can_manage_teams()):
        flash('You do not have access to the admin area.', 'danger')
        return redirect(url_for('dashboard'))
    # show matches - superadmins see all; coaches see matches involving their teams
    # support optional search q param to filter by team name/code
    q = request.args.get('q', '').strip()
    if current_user.is_coach() and not current_user.is_superadmin():
        coached_ids = [t.id for t in current_user.coached_teams]
        base_q = Match.query.filter((Match.home_team_id.in_(coached_ids)) | (Match.away_team_id.in_(coached_ids)))
    else:
        base_q = Match.query
    if q:
        teams = Team.query.filter(or_(Team.name.ilike(f"%{q}%"), Team.code == q)).all()
        ids = [t.id for t in teams]
        if ids:
            base_q = base_q.filter((Match.home_team_id.in_(ids)) | (Match.away_team_id.in_(ids)))
    matches = base_q.order_by(Match.date_time.desc()).all()
    teams = Team.query.order_by(Team.name).all()
    return render_template('admin_matches.html', matches=matches, teams=teams)


@app.route('/admin/teams')
@login_required
def admin_teams():
    # only superadmins manage teams
    if not current_user.is_superadmin():
        flash('You do not have access to the admin area.', 'danger')
        return redirect(url_for('dashboard'))
    q = request.args.get('q', '').strip()
    teams_q = Team.query
    if q:
        teams_q = teams_q.filter(or_(Team.name.ilike(f"%{q}%"), Team.code == q))
    teams = teams_q.order_by(Team.name).all()
    return render_template('admin_teams.html', teams=teams)


@app.route('/admin/team/new', methods=['GET', 'POST'])
@login_required
def admin_team_new():
    if not current_user.is_superadmin():
        flash('You do not have access to the admin area.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        code = (request.form.get('code') or '').strip()
        player_code = (request.form.get('player_code') or '').strip()
        coach_code = (request.form.get('coach_code') or '').strip()
        logo = (request.form.get('logo_filename') or '').strip()
        if not name:
            flash('Team name is required.', 'danger')
            return render_template('admin_team_form.html', team=None)
        t = Team(name=name, code=code, player_code=player_code or None, coach_code=coach_code or None, logo_filename=logo)
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
    if not current_user.is_superadmin():
        flash('You do not have access to the admin area.', 'danger')
        return redirect(url_for('dashboard'))
    t = Team.query.get_or_404(team_id)
    if request.method == 'POST':
        t.name = (request.form.get('name') or '').strip()
        t.code = (request.form.get('code') or '').strip()
        t.player_code = (request.form.get('player_code') or '').strip() or None
        t.coach_code = (request.form.get('coach_code') or '').strip() or None
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
    if not current_user.is_superadmin():
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
    # allow coaches to create matches only for teams they coach, superadmins can create any
    if not (current_user.can_edit_matches() or current_user.can_manage_teams()):
        flash('You do not have access to create matches.', 'danger')
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
            # If coach, ensure they coach one of the teams being used
            if current_user.is_coach() and not current_user.is_superadmin():
                coached_ids = [t.id for t in current_user.coached_teams]
                if home_team_id not in coached_ids and away_team_id not in coached_ids:
                    flash('Coaches may only create matches for teams they coach.', 'danger')
                    return render_template('admin_match_form.html', teams=teams, match=None)
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
    # allow coaches to edit matches for their teams and superadmins to edit any
    if not (current_user.can_edit_matches() or current_user.can_manage_teams()):
        flash('You do not have access to edit matches.', 'danger')
        return redirect(url_for('dashboard'))
    m = Match.query.get_or_404(match_id)
    if current_user.is_coach() and not current_user.is_superadmin():
        coached_ids = [t.id for t in current_user.coached_teams]
        if m.home_team_id not in coached_ids and m.away_team_id not in coached_ids:
            flash('You may only edit matches for teams you coach.', 'danger')
            return redirect(url_for('admin_matches'))
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
    teams = Team.query.order_by(Team.name).all()
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        name = request.form.get("name") or ""
        # Self-signups may optionally join a team by providing the correct team code.
        club_code = (request.form.get("club_code") or "").strip()
        team_id_raw = request.form.get('team_id')

        # Basic validation
        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("signup.html")


        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("An account with that email already exists.", "danger")
            return render_template("signup.html", teams=teams)

        # Create user
        user = User(email=email)
        user.set_password(password)
        user.set_name(name if name else email)
        user.access_level = 'regular'
        # Store any provided club_code as free-text (no DB validation)
        user.set_club("")
        user.set_club_code(club_code)
        user.set_created_by("self")

        # Persist
        # If they selected a team and provided a matching code, create a Player profile
        try:
            db.session.add(user)
            db.session.commit()
            if team_id_raw:
                try:
                    team_id = int(team_id_raw)
                    team = Team.query.get(team_id)
                    if team:
                        # coach code takes precedence
                        if team.coach_code and club_code and team.coach_code == club_code:
                            user.access_level = 'coach'
                            # add to team coaches
                            if user not in team.coaches:
                                team.coaches.append(user)
                            db.session.commit()
                        elif team.player_code and club_code and team.player_code == club_code:
                            # promote to player and add Player record
                            user.access_level = 'player'
                            p = Player(user_id=user.id, team_id=team.id)
                            db.session.add(p)
                            db.session.commit()
                except Exception:
                    db.session.rollback()
        except Exception:
            db.session.rollback()
            flash('Error creating account.', 'danger')
            return render_template('signup.html', teams=teams)

        flash("Account created — you can now log in.", "success")
        return redirect(url_for("login"))
    return render_template("signup.html", teams=teams)

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
            # Role-based redirect: use _is_admin to cover legacy numeric levels too
            if _is_admin(user):
                return redirect(url_for('admin_dashboard'))
            if user.is_coach():
                return redirect(url_for('admin_matches'))
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


# NOTE: removed temporary debug route `/whoami`.


@app.route('/admin/team/<int:team_id>/coaches/remove', methods=['POST'])
@login_required
def admin_team_coach_remove(team_id):
    if not current_user.is_superadmin():
        flash('Only superadmins may manage team coaches.', 'danger')
        return redirect(url_for('admin_teams'))
    t = Team.query.get_or_404(team_id)
    try:
        user_id = int(request.form.get('user_id'))
        u = User.query.get_or_404(user_id)
        if u in t.coaches:
            t.coaches.remove(u)
            # optionally demote the user to regular
            if hasattr(u, 'access_level'):
                u.access_level = 'regular'
            db.session.commit()
            flash('Coach removed from team.', 'success')
        else:
            flash('User was not a coach for that team.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing coach: {e}', 'danger')
    return redirect(url_for('admin_team_coaches', team_id=team_id))


@app.route('/admin/players', methods=['GET', 'POST'])
@login_required
def admin_players():
    if not current_user.is_superadmin():
        flash('Only superadmins may manage players.', 'danger')
        return redirect(url_for('admin_dashboard'))
    q = request.args.get('q', '').strip()
    if request.method == 'POST':
        # create player
        email = (request.form.get('email') or '').strip()
        name = (request.form.get('name') or '').strip()
        password = (request.form.get('password') or '').strip()
        team_id_raw = request.form.get('team_id')
        if not email or not password:
            flash('Email and password required.', 'danger')
            return redirect(url_for('admin_players'))
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('A user with that email already exists.', 'danger')
            return redirect(url_for('admin_players'))
        try:
            u = User(email=email, name=name if name else email, created_by=current_user.email, club='')
            u.set_password(password)
            u.access_level = 'player'
            db.session.add(u)
            db.session.commit()
            if team_id_raw:
                try:
                    team_id = int(team_id_raw)
                    p = Player(user_id=u.id, team_id=team_id)
                    db.session.add(p)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
            flash('Player created.', 'success')
            return redirect(url_for('admin_players'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating player: {e}', 'danger')
            return redirect(url_for('admin_players'))
    # GET
    if q:
        players = Player.query.join(User).filter(or_(User.name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%"))).all()
    else:
        players = Player.query.order_by(Player.joined_on.desc()).all()
    teams = Team.query.order_by(Team.name).all()
    return render_template('admin_players.html', players=players, teams=teams)


@app.route('/admin/player/<int:player_id>/delete', methods=['POST'])
@login_required
def admin_player_delete(player_id):
    if not current_user.is_superadmin():
        flash('Only superadmins may remove players.', 'danger')
        return redirect(url_for('admin_players'))
    p = Player.query.get_or_404(player_id)
    try:
        # demote user to regular and delete player profile
        u = p.user
        db.session.delete(p)
        if hasattr(u, 'access_level'):
            u.access_level = 'regular'
        db.session.commit()
        flash('Player removed.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing player: {e}', 'danger')
    return redirect(url_for('admin_players'))


@app.route('/coach/team/<int:team_id>/player/<int:player_id>/delete', methods=['POST'])
@login_required
def coach_player_delete(team_id, player_id):
    t = Team.query.get_or_404(team_id)
    # allow only coaches of this team or superadmins
    if not (current_user.is_superadmin() or (current_user.is_coach() and t in current_user.coached_teams)):
        flash('You do not have permission to remove players for this team.', 'danger')
        return redirect(url_for('dashboard'))
    p = Player.query.get_or_404(player_id)
    if p.team_id != team_id:
        flash('Player is not a member of this team.', 'danger')
        return redirect(url_for('coach_team_players', team_id=team_id))
    try:
        u = p.user
        db.session.delete(p)
        if hasattr(u, 'access_level'):
            u.access_level = 'regular'
        db.session.commit()
        flash('Player removed from team.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing player: {e}', 'danger')
    return redirect(url_for('coach_team_players', team_id=team_id))


@app.route('/admin/match/<int:match_id>/delete', methods=['POST'])
@login_required
def admin_match_delete(match_id):
    if not (current_user.can_edit_matches() or current_user.can_manage_teams()):
        flash('You do not have permission to delete matches.', 'danger')
        return redirect(url_for('dashboard'))
    m = Match.query.get_or_404(match_id)
    if current_user.is_coach() and not current_user.is_superadmin():
        coached_ids = [t.id for t in current_user.coached_teams]
        if m.home_team_id not in coached_ids and m.away_team_id not in coached_ids:
            flash('You may only delete matches for teams you coach.', 'danger')
            return redirect(url_for('admin_matches'))
    try:
        db.session.delete(m)
        db.session.commit()
        flash('Match deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting match: {e}', 'danger')
    return redirect(url_for('admin_matches'))


# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)


