from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# association table for users tracking teams
user_tracked_teams = db.Table(
    'user_tracked_teams',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    # access_level: 'regular' | 'player' | 'coach' | 'superadmin'
    access_level = db.Column(db.String(50), default='regular')
    name = db.Column(db.String(150), nullable=False)
    created_by = db.Column(db.String, nullable=False)
    club = db.Column(db.String(150), nullable=False)
    # NOTE: removed duplicate `account_type` field — use `access_level` exclusively
    # optional club code (references Club.code)
    club_code = db.Column(db.String(64), nullable=True)
    
    # relationship for tracked teams
    tracked_teams = db.relationship('Team', secondary='user_tracked_teams', backref=db.backref('followers', lazy='dynamic'))

    def set_access_level(self, level):
        self.access_level = level

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def set_name(self, name):
        self.name = name

    def set_created_by(self, creator):
        self.created_by = creator

    def set_club(self, club):
        # legacy method: store human-friendly club name
        self.club = club

    def set_club_code(self, code):
        # store club code (short identifier) if present
        self.club_code = code

    # Convenience helpers for role checks
    def is_superadmin(self):
        lvl = self.access_level
        if lvl is None:
            return False
        # support legacy numeric levels (e.g. '2') as well as textual roles
        try:
            return int(lvl) >= 2
        except Exception:
            return str(lvl).lower() in ('superadmin', 'admin')

    def is_coach(self):
        lvl = self.access_level
        if lvl is None:
            return False
        try:
            return int(lvl) == 1
        except Exception:
            return str(lvl).lower() == 'coach'

    def is_player(self):
        # Determine if this user is a player by checking `access_level`.
        lvl = self.access_level
        if lvl is None:
            return False
        try:
            return int(lvl) == 0
        except Exception:
            return str(lvl).lower() == 'player'

    def can_manage_teams(self):
        return self.is_superadmin()

    def can_edit_matches(self):
        return self.is_coach() or self.is_superadmin()

    def can_view_all(self):
        return self.is_superadmin()



class Team(db.Model):
    __tablename__ = 'team'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(64), unique=True, nullable=True)
    logo_filename = db.Column(db.String(256), nullable=True)

    # relationships (players and coaches)
    players = db.relationship('Player', backref='team', lazy='dynamic')
    coaches = db.relationship('User', secondary='team_coaches', backref=db.backref('coached_teams', lazy='dynamic'))

    def __repr__(self):
        return f"<Team {self.name}>"


# association table linking teams and coach users
team_coaches = db.Table(
    'team_coaches',
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)


class Player(db.Model):
    __tablename__ = 'player'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    squad_number = db.Column(db.String(16), nullable=True)
    position = db.Column(db.String(64), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    joined_on = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)

    # relationship back to the User record
    user = db.relationship('User', backref=db.backref('player_profile', uselist=False))

    def __repr__(self):
        return f"<Player {self.id} user={self.user_id} team={self.team_id}>"


class Match(db.Model):
    __tablename__ = 'match'
    id = db.Column(db.Integer, primary_key=True)
    home_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    location = db.Column(db.String(255), nullable=True)
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)

    # relationships
    home_team = db.relationship('Team', foreign_keys=[home_team_id], backref='home_matches')
    away_team = db.relationship('Team', foreign_keys=[away_team_id], backref='away_matches')

    def is_past(self):
        if self.home_score is not None and self.away_score is not None:
            return True
        return self.date_time < datetime.utcnow()

    def result_for_home(self):
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return 'win'
        if self.home_score < self.away_score:
            return 'loss'
        return 'draw'

    def __repr__(self):
        return f"<Match {self.id}: {self.home_team_id} vs {self.away_team_id} @ {self.date_time}>"


class Leaderboard(db.Model):
    __tablename__ = 'leaderboard'
    id = db.Column(db.Integer, primary_key=True)
    team = db.Column(db.String(200), nullable=False)
    # rank will be computed after inserts (higher `pts_scored` => better rank)
    rank = db.Column(db.Integer, nullable=True)
    pl = db.Column(db.Integer, nullable=False, default=0)
    w = db.Column(db.Integer, nullable=False, default=0)
    l = db.Column(db.Integer, nullable=False, default=0)
    d = db.Column(db.Integer, nullable=False, default=0)
    pts_f = db.Column(db.Integer, nullable=False, default=0)
    pts_ag = db.Column(db.Integer, nullable=False, default=0)
    pts_diff = db.Column(db.Integer, nullable=False, default=0)
    g_pts = db.Column(db.Integer, nullable=False, default=0)
    b_pts = db.Column(db.Integer, nullable=False, default=0)
    total = db.Column(db.Integer, nullable=False, default=0)
    pts_scored = db.Column(db.Integer, nullable=False, default=0)
    created_on = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)

    def __repr__(self):
        return f"<Leaderboard {self.id} team={self.team} rank={self.rank} pts_scored={self.pts_scored}>"
    
