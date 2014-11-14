from app.flask_app import db

class User(db.Model):
	username = db.Column(db.String(32), primary_key=True)
	# SHA-512 returns a 512-bit hash, which is 512 bits / 8 bits per byte * 2 hex digits per byte = 128 hex digits.
	password = db.Column(db.String(128), nullable=False)
	# 254 is the maximum length of an email address.
	email = db.Column(db.String(254), nullable=False)
	first_name = db.Column(db.String(50), nullable=False)
	last_name = db.Column(db.String(50), nullable=False)

	def __init__(self, username, password, email, first_name, last_name):
		self.username = username;
		self.password = password;
		self.email = email;
		self.first_name = first_name;
		self.last_name = last_name;

	def __repr__(self):
		return '<User %r>' % (self.username)
