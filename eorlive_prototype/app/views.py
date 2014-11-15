from flask import render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from app.flask_app import app, lm, db
from app import models
import requests
import json
import hashlib

@app.route('/')
@app.route('/index')
def index():
	return render_template('index.html')

@app.route('/get_observations', methods = ['POST'])
def get_observations():
	starttime = int(request.form['starttime'])
	endtime = int(request.form['endtime'])
	session['starttime'] = starttime
	session['endtime'] = endtime

	requestURL = 'http://ngas01.ivec.org/metadata/find'

	params = {'projectid': 'G0009', 'mintime': starttime, 'maxtime': endtime}

	data = requests.get(requestURL, params=params).text

	observations = json.loads(data)

	return render_template('observation_table.html', observations=observations)

@app.before_request
def before_request():
	g.user = current_user

@lm.user_loader
def load_user(id):
	return models.User.query.get(id)

@app.route('/login', methods = ['GET', 'POST'])
def login():
	if g.user is not None and g.user.is_authenticated():
		return redirect(url_for('index'))
	error = None
	if request.method == 'POST':
		username = request.form['username'].strip()
		password = request.form['password'].strip()
		
		u = models.User.query.get(username)
		password = password.encode('UTF-8')
		if not u:
			error = 'Invalid username/password combination.'
		elif u.password != hashlib.sha512(password).hexdigest():
			error = 'Invalid username/password combination.'
		else:
			login_user(u)
			flash('You were logged in')
			return redirect(url_for('index'))
	return render_template('login.html', error=error)

@app.route('/logout')
def logout():
	logout_user()
	flash('You were logged out')
	return redirect(url_for('index'))
