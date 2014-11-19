from flask import render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from app.flask_app import app, lm, db
from app import models
import requests
import json
import hashlib
from requests_futures.sessions import FuturesSession
from sqlalchemy import and_
from datetime import datetime

@app.route('/')
@app.route('/index')
def index():
	return render_template('index.html')

@app.route('/get_observations', methods = ['POST'])
def get_observations():
	session = FuturesSession()

	baseUTCToGPSURL = 'http://ngas01.ivec.org/metadata/tconv/?utciso='

	requestURLStart = baseUTCToGPSURL + request.form['starttime']

	requestURLEnd = baseUTCToGPSURL + request.form['endtime']

	#Start the first Web service request in the background.
	future_start = session.get(requestURLStart)

	#The second request is started immediately.
	future_end = session.get(requestURLEnd)

	#Wait for the first request to complete, if it hasn't already.
	response_start = future_start.result()

	#Wait for the second request to complete, if it hasn't already.
	response_end = future_end.result()

	startGPS = response_start.content

	endGPS = response_end.content

	requestURL = 'http://ngas01.ivec.org/metadata/find'

	params = {'projectid': 'G0009', 'mintime': startGPS, 'maxtime': endGPS}

	data = requests.get(requestURL, params=params).text

	observations = json.loads(data)

	return render_template('observation_table.html', observations=observations)

@app.route('/graph_data', methods = ['POST'])
def graph_data():
	query = models.GraphData.query

	# Get graph data for the range specified by the user. The values being compared here are strings representing UTC time; comparing dates like this is fine.
	query = query.filter(and_(models.GraphData.created_on >= request.form['starttime'], models.GraphData.created_on <= request.form['endtime']))

	# Order the data by the "created_on" field. This data is going to be used in a chart, so the data needs to be in time-series order.
	graph_data = [gd.asDict() for gd in query.order_by(models.GraphData.created_on).all()]

	# Each data point is paired with its creation time. Highcharts needs the data in this format for the x-axis to work properly.
	hours_scheduled = [[gd['created_on'], gd['hours_scheduled']] for gd in graph_data]

	hours_observed = [[gd['created_on'], gd['hours_observed']] for gd in graph_data]

	hours_with_data = [[gd['created_on'], gd['hours_with_data']] for gd in graph_data]

	hours_with_uvfits = [[gd['created_on'], gd['hours_with_uvfits']] for gd in graph_data]

	return render_template('line_chart.html', hours_scheduled = hours_scheduled, hours_observed = hours_observed,
		hours_with_data = hours_with_data, hours_with_uvfits = hours_with_uvfits)

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
