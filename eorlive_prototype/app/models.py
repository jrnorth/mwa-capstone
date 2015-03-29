from app.flask_app import db
from datetime import datetime

set_subscriptions = db.Table('set_subscriptions',
    db.Column('username', db.String(32), db.ForeignKey('user.username')),
    db.Column('set_id', db.Integer, db.ForeignKey('set.id'))
)

class User(db.Model):
    username = db.Column(db.String(32), primary_key=True)
    # SHA-512 returns a 512-bit hash, which is 512 bits / 8 bits per byte * 2 hex digits per byte = 128 hex digits.
    password = db.Column(db.String(128), nullable=False)
    # 254 is the maximum length of an email address.
    email = db.Column(db.String(254), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    owned_sets = db.relationship('Set', backref='user')
    subscribed_sets = db.relationship('Set', secondary=set_subscriptions)

    def __init__(self, username, password, email, first_name, last_name):
        self.username = username;
        self.password = password;
        self.email = email;
        self.first_name = first_name;
        self.last_name = last_name;

    def __repr__(self):
        return '<User %r>' % (self.username)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.username

class Set(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), db.ForeignKey('user.username'))
    name = db.Column(db.String(50))
    start = db.Column(db.Integer)
    end = db.Column(db.Integer)
    low_or_high = db.Column(db.String(4)) # Whether this set contains 'low', 'high', or 'any' observations.
    eor = db.Column(db.String(4)) # Whether this set contains 'EOR0', 'EOR1', or 'any' observations.
    total_data_hrs = db.Column(db.Float)
    flagged_data_hrs = db.Column(db.Float)

class FlaggedSubset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    set_id = db.Column(db.Integer, db.ForeignKey('set.id'))
    start = db.Column(db.Integer)
    end = db.Column(db.Integer)

class FlaggedObsIds(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    obs_id = db.Column(db.Integer)
    flagged_subset_id = db.Column(db.Integer, db.ForeignKey('flagged_subset.id'))

class GraphData(db.Model):
    # AUTO_INCREMENT is automatically set on the first Integer primary key column that is not marked as a foreign key.
    id = db.Column(db.Integer, primary_key=True)
    # Store a 'created_on' string field for the current time that is automatically inserted with a new entry into the database.
    # We're using UTC time, so that's why there is a Z at the end of the string.
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    hours_scheduled = db.Column(db.Float)
    hours_observed = db.Column(db.Float)
    hours_with_data = db.Column(db.Float)
    hours_with_uvfits = db.Column(db.Float)
    data_transfer_rate = db.Column(db.Float)

    def asDict(self):
        return {
            'id': self.id,
            'created_on': self.created_on,
            'hours_scheduled': round(self.hours_scheduled or 0., 4),
            'hours_observed': round(self.hours_observed or 0., 4),
            'hours_with_data': round(self.hours_with_data or 0., 4),
            'hours_with_uvfits': round(self.hours_with_uvfits or 0., 4),
            'data_transfer_rate': round(self.data_transfer_rate or 0., 4)
        }

class Thread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(32), db.ForeignKey('user.username'))
    created_on = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    text = db.Column(db.String(1000), nullable=False)
    username = db.Column(db.String(32), db.ForeignKey('user.username'))
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
