from flask import render_template, flash, redirect, session, url_for, request, g, make_response
from flask.ext.login import login_user, logout_user, current_user, login_required
from app.flask_app import app, lm, db
from app import models
import requests
import json
import hashlib
from requests_futures.sessions import FuturesSession
from sqlalchemy import and_, func
from datetime import datetime
import psycopg2
import os

def send_query(db, query):
	cur = db.cursor()
	cur.execute(query)
	return cur

@app.route('/')
@app.route('/index')
def index():
	# GET is the default request method.
	# Since we're using GET, we have to access arguments by request.args.get() rather than request.form[]
	return render_template('index.html', starttime=request.args.get('starttime'), endtime=request.args.get('endtime'))

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

@app.route('/histogram_data', methods = ['POST'])
def histogram_data():
	startdatetime = datetime.strptime(request.form['starttime'], '%Y-%m-%dT%H:%M:%SZ')

	enddatetime = datetime.strptime(request.form['endtime'], '%Y-%m-%dT%H:%M:%SZ')

	session = FuturesSession()

	baseUTCToGPSURL = 'http://ngas01.ivec.org/metadata/tconv/?utciso='

	requestURLStart = baseUTCToGPSURL + request.form['starttime']

	requestURLEnd = baseUTCToGPSURL + request.form['endtime']

	#Start the first Web service request in the background.
	future_start = session.get(requestURLStart)

	#The second request is started immediately.
	future_end = session.get(requestURLEnd)

	julian_datetime_start = startdatetime
	#Get the start of the Julian day (12:00 UT) corresponding to the start datetime.
	if (startdatetime.hour < 12): #If the hour wasn't >= 12, then the start of this Julian day was the previous day at 12:00 UT.
		julian_datetime_start = julian_datetime_start - datetime.timedelta(hours = 12)
	#No matter whether the hour was >= 12, the start of the Julian day is at 12:00 UT.
	julian_datetime_start = julian_datetime_start.replace(hour=12, minute=0, second=0, microsecond=0)

	requestURLJulianStart = baseUTCToGPSURL + julian_datetime_start.strftime('%Y-%m-%dT%H:%M:%SZ')
	#Start a Web request for the GPS time corresponding to the exact start of the start datetime's Julian day in the background.
	future_julian_start = session.get(requestURLJulianStart)

	#Wait for the first request to complete, if it hasn't already.
	start_gps = int(future_start.result().content)

	#Wait for the second request to complete, if it hasn't already.
	end_gps = int(future_end.result().content)

	response = send_query(g.eor_db, '''SELECT starttime, obsname
					FROM mwa_setting
					WHERE starttime >= {} AND starttime <= {}
					AND projectid='G0009'
					ORDER BY starttime ASC'''.format(start_gps, end_gps)).fetchall()

	if len(response) > 0:
		# The Julian day for January 1, 2000 12:00 UT was 2,451,545 (http://en.wikipedia.org/wiki/Julian_day).
		jan_1_2000 = datetime(2000, 1, 1, 12)

		jan_1_2000_julian_day = 2451545

		delta_start = startdatetime - jan_1_2000

		julian_day_start = delta_start.days + jan_1_2000_julian_day	

		delta_end = enddatetime - jan_1_2000

		julian_day_end = delta_end.days + jan_1_2000_julian_day

		observation_counts = [0 for day in range(julian_day_start, julian_day_end + 1)]

		julian_days = [x for x in range(julian_day_start, julian_day_end + 1)]
		#Wait for this Web request to complete, if it hasn't already.
		julian_start_gps = int(future_julian_start.result().content)

		SECONDS_PER_DAY = 86400

		for observation in response:
			obs_counts_index = 0
			try: #Most of the observation names end with the 7-digit Julian day, so we can just grab it from there.
				obs_counts_index = int(observation[1][-7:]) - julian_day_start
			except ValueError as ve:
				#If we couldn't get an integer from the observation name, we have to calculate the Julian day using the GPS time of the
				#start datetime and calculating how many days occurred between it and the observation in question.
				obs_counts_index = int((observation[0] - julian_start_gps) / SECONDS_PER_DAY)
			observation_counts[obs_counts_index] = observation_counts[obs_counts_index] + 1

	return render_template('histogram.html', julian_days=julian_days, observation_counts=observation_counts)

@app.before_request
def before_request():
	g.user = current_user
	try :
		g.eor_db = psycopg2.connect(database='mwa', host='eor-db.mit.edu', user=os.environ['MWA_DB_USERNAME'], password=os.environ['MWA_DB_PW'])
	except Exception as e:
		print("Can't connect to the eor database at eor-db.mit.edu - %s" % e)

@app.teardown_request
def teardown_request(exception):
	eor_db = getattr(g, 'eor_db', None)
	if eor_db is not None:
		eor_db.close()

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

@app.route('/profile')
def profile():
	if (g.user is not None and g.user.is_authenticated()):
		user = models.User.query.get(g.user.username)
		return render_template('profile.html', user=user)
	else:
		return redirect(url_for('login'))

@app.route('/range_saved', methods = ['POST'])
def range_saved():
	if (g.user is not None and g.user.is_authenticated()):
		start = request.form['starttime']

		end = request.form['endtime']

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

		startGPS = int(response_start.content)

		endGPS = int(response_end.content)

		range_saved = False

		range_id = -1

		user = models.User.query.get(g.user.username)

		for ran in user.saved_ranges:
			if ran.start == startGPS and ran.end == endGPS:
				range_saved = True
				range_id = ran.id
				break

		return render_template('range_save_button.html', range_saved=range_saved, range_id=int(range_id), rangeStart=int(startGPS), rangeEnd=int(endGPS))
	else:
		return '<span>Log in to save ranges</span>'

@app.route('/save_range', methods = ['POST'])
def save_range():
	if (g.user is not None and g.user.is_authenticated()):
		startGPS = request.form['startGPS']

		endGPS = request.form['endGPS']

		user = models.User.query.get(g.user.username)

		for ran in user.saved_ranges:
			if ran.start == startGPS and ran.end == endGPS:
				return str(ran.id)

		ran = models.Range.query.filter(and_(models.Range.start == startGPS, models.Range.end == endGPS)).first()

		if ran is not None:
			user.saved_ranges.append(ran)
			db.session.merge(user)
			db.session.commit()
			return str(ran.id)

		ran = models.Range()
		ran.start = startGPS
		ran.end = endGPS

		user.saved_ranges.append(ran)

		db.session.add(ran)
		db.session.commit()

		db.session.refresh(ran)

		return str(ran.id)
	else:
		return make_response('Error: no user logged in', 401)

@app.route('/remove_range', methods = ['POST'])
def remove_range():
	if (g.user is not None and g.user.is_authenticated()):
		range_id = int(request.form['range_id'])

		user = models.User.query.get(g.user.username)

		ran = None

		for ran_iter in user.saved_ranges:
			if ran_iter.id == range_id:
				ran = ran_iter
				break

		if ran is None:
			return make_response('Error: user doesn\'t have that range', 500)

		user.saved_ranges.remove(ran)
		db.session.commit()

		return json.dumps({'start': ran.start, 'end': ran.end})
	else:
		return make_response('Error: no user logged in', 401)
