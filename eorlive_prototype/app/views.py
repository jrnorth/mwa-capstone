from flask import render_template, flash, redirect, session, url_for, request, g
from app.flask_app import app
import requests
import json

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

@app.route('/login', methods = ['GET', 'POST'])
def login():
	error = None
	if request.method == 'POST':
		username = request.form['username'].strip()
		password = request.form['password'].strip()
		if not username:
			error = 'Invalid username'
		elif not password:
			error = 'Invalid password'
		else:
			session['logged_in'] = True
			flash('You were logged in')
			return redirect(url_for('index'))
	# It wasn't a POST request, so the user was redirected to this page.
	return render_template('login.html', error=error)

@app.route('/logout')
def logout():
	# Delete the 'logged_in' key from the dictionary (or do nothing if the key is not there).
	# This means we don't have to check whether the user was logged in.
	session.pop('logged_in', None)
	flash('You were logged out')
	return redirect(url_for('index'))
