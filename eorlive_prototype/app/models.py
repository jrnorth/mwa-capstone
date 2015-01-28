from app.flask_app import db
from datetime import datetime

user_range = db.Table('user_range',
	db.Column('user', db.String(32), db.ForeignKey('user.username')),
	db.Column('range_id', db.Integer, db.ForeignKey('range.id'))
)

class User(db.Model):
	username = db.Column(db.String(32), primary_key=True)
	# SHA-512 returns a 512-bit hash, which is 512 bits / 8 bits per byte * 2 hex digits per byte = 128 hex digits.
	password = db.Column(db.String(128), nullable=False)
	# 254 is the maximum length of an email address.
	email = db.Column(db.String(254), nullable=False)
	first_name = db.Column(db.String(50), nullable=False)
	last_name = db.Column(db.String(50), nullable=False)
	saved_ranges = db.relationship('Range', secondary=user_range)
	comments = db.relationship('Comment', backref='user', lazy='dynamic')

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

class Range(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	start = db.Column(db.Integer)
	end = db.Column(db.Integer)

class GraphData(db.Model):
	# AUTO_INCREMENT is automatically set on the first Integer primary key column that is not marked as a foreign key.
	id = db.Column(db.Integer, primary_key=True)
	# Store a 'created_on' string field for the current time that is automatically inserted with a new entry into the database.
	# We're using UTC time, so that's why there is a Z at the end of the string.
	created_on = db.Column(db.String(20), default=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))
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

class HistogramData(db.Model):
	obs_id = db.Column(db.Integer, primary_key=True, autoincrement=False)
	julian_day = db.Column(db.Integer)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id 
    text = db.Column(db.String(1000), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    comment_id = db.Column(db.Integer, db.ForeignKey('range.id'))	