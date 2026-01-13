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

# Initialize extensions with the app-
db.init_app(app)
login_manager.init_app(app)
# Ensure Flask-Login redirects unauthenticated users to our login page
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from models import User, Team, Match, Player, Leaderboard
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
    # show public leaderboards ordered by rank (if present) then pts_scored
    try:
        rows = Leaderboard.query.order_by(Leaderboard.rank.asc().nullsfirst(), Leaderboard.pts_scored.desc()).all()
    except Exception:
        rows = []
    return render_template("leaderboards.html", rows=rows)

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
        leaderboards = Leaderboard.query.order_by(Leaderboard.rank.asc().nullsfirst() if hasattr(Leaderboard, 'rank') else Leaderboard.rank.asc()).all()
    except Exception:
        matches = []
        leaderboards = []
    return render_template("tables.html", matches=matches, leaderboards=leaderboards)

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
    
    # If this user is an admin (including legacy numeric roles), send them to the admin dashboard
    if _is_admin(current_user):
        return redirect(url_for('admin_dashboard'))
    
    # Regular user dashboard with team tracking
    teams = Team.query.order_by(Team.name).all()
    tracked_teams = current_user.tracked_teams
    tracked_team_ids = [t.id for t in tracked_teams]
    
    # Get upcoming matches for tracked teams
    now = datetime.utcnow()
    upcoming_matches = []
    if tracked_teams:
        for team in tracked_teams:
            matches = Match.query.filter(
                ((Match.home_team_id == team.id) | (Match.away_team_id == team.id)) & (Match.date_time >= now)
            ).order_by(Match.date_time.asc()).limit(5).all()
            upcoming_matches.extend(matches)
        # Sort by date and remove duplicates
        upcoming_matches = sorted(set(upcoming_matches), key=lambda m: m.date_time)[:10]
    
    return render_template("dashboard.html", teams=teams, tracked_teams=tracked_teams, 
                         tracked_team_ids=tracked_team_ids, upcoming_matches=upcoming_matches)


@app.route("/dashboard/track/<int:team_id>", methods=['POST'])
@login_required
def dashboard_track_team(team_id):
    team = Team.query.get_or_404(team_id)
    
    if team in current_user.tracked_teams:
        # Unfollow
        current_user.tracked_teams.remove(team)
        flash(f'You are no longer following {team.name}.', 'info')
    else:
        # Follow
        current_user.tracked_teams.append(team)
        flash(f'You are now following {team.name}!', 'success')
    
    db.session.commit()
    return redirect(url_for('dashboard'))


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


@app.route('/admin/leaderboards', methods=['GET', 'POST'])
@login_required
def admin_leaderboards():
    # only superadmins may manage leaderboards
    if not current_user.is_superadmin():
        flash('Only superadmins may manage leaderboards.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        # read form fields and create a new leaderboard row
        team = (request.form.get('team') or '').strip()
        try:
            pl = int(request.form.get('pl') or 0)
            w = int(request.form.get('w') or 0)
            d = int(request.form.get('d') or 0)
            l = int(request.form.get('l') or 0)
            pts_f = int(request.form.get('pts_f') or 0)
            pts_ag = int(request.form.get('pts_ag') or 0)
            pts_diff = int(request.form.get('pts_diff') or (pts_f - pts_ag))
            g_pts = int(request.form.get('g_pts') or 0)
            b_pts = int(request.form.get('b_pts') or 0)
            total = int(request.form.get('total') or 0)
            pts_scored = int(request.form.get('pts_scored') or 0)
        except ValueError:
            flash('Numeric fields must be integers.', 'danger')
            return redirect(url_for('admin_leaderboards'))

        if not team:
            flash('Team name is required.', 'danger')
            return redirect(url_for('admin_leaderboards'))

        try:
            lb = Leaderboard(team=team, pl=pl, w=w, d=d, l=l, pts_f=pts_f, pts_ag=pts_ag, pts_diff=pts_diff, g_pts=g_pts, b_pts=b_pts, total=total, pts_scored=pts_scored)
            db.session.add(lb)
            db.session.commit()
            # recompute ranks ordered by pts_scored desc
            rows = Leaderboard.query.order_by(Leaderboard.pts_scored.desc()).all()
            for idx, row in enumerate(rows, start=1):
                row.rank = idx
            db.session.commit()
            flash('Leaderboard row added and ranks updated.', 'success')
            return redirect(url_for('admin_leaderboards'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating leaderboard row: {e}', 'danger')
            return redirect(url_for('admin_leaderboards'))

    # GET: show current leaderboard rows ordered by rank
    try:
        rows = Leaderboard.query.order_by(Leaderboard.rank.asc().nullsfirst(), Leaderboard.pts_scored.desc()).all()
    except Exception:
        rows = []
    return render_template('admin_leaderboards.html', rows=rows)


@app.route('/admin/leaderboards/<int:row_id>/edit', methods=['POST'])
@login_required
def admin_leaderboards_edit(row_id):
    if not current_user.is_superadmin():
        flash('Only superadmins may manage leaderboards.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    row = Leaderboard.query.get_or_404(row_id)
    
    try:
        row.team = (request.form.get('team') or '').strip() or row.team
        row.pl = int(request.form.get('pl') or row.pl)
        row.w = int(request.form.get('w') or row.w)
        row.d = int(request.form.get('d') or row.d)
        row.l = int(request.form.get('l') or row.l)
        row.pts_f = int(request.form.get('pts_f') or row.pts_f)
        row.pts_ag = int(request.form.get('pts_ag') or row.pts_ag)
        row.pts_diff = int(request.form.get('pts_diff') or (row.pts_f - row.pts_ag))
        row.g_pts = int(request.form.get('g_pts') or row.g_pts)
        row.b_pts = int(request.form.get('b_pts') or row.b_pts)
        row.total = int(request.form.get('total') or row.total)
        row.pts_scored = int(request.form.get('pts_scored') or row.pts_scored)
        
        db.session.commit()
        
        # recompute ranks
        rows = Leaderboard.query.order_by(Leaderboard.pts_scored.desc()).all()
        for idx, r in enumerate(rows, start=1):
            r.rank = idx
        db.session.commit()
        
        flash('Leaderboard row updated and ranks recalculated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating leaderboard row: {e}', 'danger')
    
    return redirect(url_for('admin_leaderboards'))


@app.route('/admin/leaderboards/<int:row_id>/delete', methods=['POST'])
@login_required
def admin_leaderboards_delete(row_id):
    if not current_user.is_superadmin():
        flash('Only superadmins may manage leaderboards.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    row = Leaderboard.query.get_or_404(row_id)
    team_name = row.team
    
    try:
        db.session.delete(row)
        db.session.commit()
        
        # recompute ranks
        rows = Leaderboard.query.order_by(Leaderboard.pts_scored.desc()).all()
        for idx, r in enumerate(rows, start=1):
            r.rank = idx
        db.session.commit()
        
        flash(f'Leaderboard row for {team_name} deleted and ranks recalculated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting leaderboard row: {e}', 'danger')
    
    return redirect(url_for('admin_leaderboards'))


# Admin: list and manage matches
@app.route('/admin/matches')
@login_required
def admin_matches():
    # allow superadmins full access; allow coaches to view/edit matches for teams they coach
    if not (current_user.can_edit_matches() or current_user.can_manage_teams()):
        flash('You do not have access to the admin area.', 'danger')
        return redirect(url_for('dashboard'))
    # show matches - superadmins see all; coaches see matches involving their teams
    if current_user.is_coach() and not current_user.is_superadmin():
        coached_ids = [t.id for t in current_user.coached_teams]
        matches = Match.query.filter(
            (Match.home_team_id.in_(coached_ids)) | (Match.away_team_id.in_(coached_ids))
        ).order_by(Match.date_time.desc()).all()
    else:
        matches = Match.query.order_by(Match.date_time.desc()).all()
    teams = Team.query.order_by(Team.name).all()
    return render_template('admin_matches.html', matches=matches, teams=teams)


@app.route('/admin/teams')
@login_required
def admin_teams():
    # only superadmins manage teams
    if not current_user.is_superadmin():
        flash('You do not have access to the admin area.', 'danger')
        return redirect(url_for('dashboard'))
    teams = Team.query.order_by(Team.name).all()
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
    if not current_user.is_superadmin():
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
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        name = request.form.get("name") or ""
        # Self-signups create only regular accounts. Roles (coach/player) are assigned by admins.
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
        user.access_level = 'regular'
        # Store any provided club_code as free-text (no DB validation)
        user.set_club("N/A")
        user.set_club_code(club_code)
        user.set_created_by("self")

        # Persist
        try:
            db.session.add(user)
            db.session.commit()
            flash("Account created — you can now log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating account: {e}", "danger")
            return render_template("signup.html")

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


# DEBUG: temporary route to inspect currently-logged-in user (remove in production)
@app.route('/whoami')
@login_required
def whoami():
    info = []
    info.append(f"email: {getattr(current_user, 'email', None)}")
    info.append(f"access_level: {getattr(current_user, 'access_level', None)}")
    # role helper presence
    info.append(f"is_superadmin: {getattr(current_user, 'is_superadmin', lambda: 'n/a')()}")
    info.append(f"is_coach: {getattr(current_user, 'is_coach', lambda: 'n/a')()}")
    info.append(f"is_player: {getattr(current_user, 'is_player', lambda: 'n/a')()}")
    return '<br>'.join(info)


# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)


