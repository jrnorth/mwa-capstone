from flask import render_template, flash, redirect, session, url_for, request, g, make_response
from flask.ext.login import login_user, logout_user, current_user, login_required
from app.flask_app import app, lm, db
from app import models
import requests
import json
import hashlib
from requests_futures.sessions import FuturesSession
from sqlalchemy import and_, func, or_
from datetime import datetime, timedelta
import psycopg2
import os

def send_query(db, query):
	cur = db.cursor()
	cur.execute(query)
	return cur

@app.route('/')
@app.route('/index')
@app.route('/index/set/<setName>')
@app.route('/set/<setName>')
def index(setName = None):
	# GET is the default request method.
	# Since we're using GET, we have to access arguments by request.args.get() rather than request.form[]

	if setName is not None:
		session = FuturesSession()

		theSet = models.Set.query.filter(and_(models.Set.name == setName)).first()

		if (g.user is not None and g.user.is_authenticated()):
			if theSet is not None:
				comments = theSet.comments
				if comments is not None:
					return render_template('setView.html', setName=theSet.name, comments=comments, set_id=theSet.id, setStart=theSet.start, setEnd=theSet.end)
				else: #set with no comments
					return render_template('setView.html', setName=theSet.name, set_id=theSet.id, setStart=theSet.start, setEnd=theSet.end)
			else: #no set, just show index
				return render_template('index.html')
		else: #logged out view
			return render_template('setView.html', setName=theSet.name, set_id=theSet.id, setStart=theSet.start, setEnd=theSet.end, logged_out=True)
	else: #original case in index
		return render_template('index.html', starttime=request.args.get('starttime'), endtime=request.args.get('endtime'))

@app.route('/data_amount', methods = ['GET'])
def data_amount():
	query = models.GraphData.query

	data = query.order_by(models.GraphData.created_on.desc()).first()

	data_time = hours_scheduled = hours_observed = hours_with_data = hours_with_uvfits = 'N/A'

	if data is not None:
		data = data.asDict()
		data_time = data['created_on']
		hours_scheduled = data['hours_scheduled']
		hours_observed = data['hours_observed']
		hours_with_data = data['hours_with_data']
		hours_with_uvfits = data['hours_with_uvfits']

	return render_template('data_amount_table.html', hours_scheduled=hours_scheduled, hours_observed=hours_observed,
		hours_with_data=hours_with_data, hours_with_uvfits=hours_with_uvfits, data_time=data_time)

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
		julian_datetime_start = julian_datetime_start - timedelta(hours = 12)
	#No matter whether the hour was >= 12, the start of the Julian day is at 12:00 UT.
	julian_datetime_start = julian_datetime_start.replace(hour=12, minute=0, second=0, microsecond=0)

	requestURLJulianStart = baseUTCToGPSURL + julian_datetime_start.strftime('%Y-%m-%dT%H:%M:%SZ')
	#Start a Web request for the GPS time corresponding to the exact start of the start datetime's Julian day in the background.
	future_julian_start = session.get(requestURLJulianStart)

	#Wait for the first request to complete, if it hasn't already.
	start_gps = int(future_start.result().content)

	#Wait for the second request to complete, if it hasn't already.
	end_gps = int(future_end.result().content)

	leap_seconds_result = send_query(g.eor_db, "SELECT leap_seconds FROM leap_seconds ORDER BY leap_seconds DESC LIMIT 1").fetchone()

	leap_seconds = leap_seconds_result[0]

	GPS_LEAP_SECONDS_OFFSET = leap_seconds - 19

	response = send_query(g.eor_db, '''SELECT starttime, obsname, ra_phase_center
					FROM mwa_setting
					WHERE starttime >= {} AND starttime <= {}
					AND projectid='G0009'
					ORDER BY starttime ASC'''.format(start_gps, end_gps)).fetchall()

	obscontroller_response = send_query(g.eor_db, '''SELECT FLOOR(reference_time) AS reference_time
							FROM obscontroller_log
							WHERE reference_time >= {} AND reference_time <= {}
							ORDER BY reference_time ASC'''.format(start_gps, end_gps)).fetchall()

	recvstatuspolice_response = send_query(g.eor_db, '''SELECT FLOOR(reference_time) AS reference_time
							FROM recvstatuspolice_log
							WHERE reference_time >= {} AND reference_time <= {}
							ORDER BY reference_time ASC'''.format(start_gps, end_gps)).fetchall()

	# The Julian day for January 1, 2000 12:00 UT was 2,451,545 (http://en.wikipedia.org/wiki/Julian_day).
	jan_1_2000 = datetime(2000, 1, 1, 12)

	jan_1_2000_julian_day = 2451545

	delta_start = startdatetime - jan_1_2000

	julian_day_start = delta_start.days + jan_1_2000_julian_day

	delta_end = enddatetime - jan_1_2000

	julian_day_end = delta_end.days + jan_1_2000_julian_day

	jan_1_1970 = datetime(1970, 1, 1)

	jan_6_1980 = datetime(1980, 1, 6)

	GPS_UTC_DELTA = (jan_6_1980 - jan_1_1970).total_seconds()

	low_eor0_counts = []

	high_eor0_counts = []

	low_eor1_counts = []

	high_eor1_counts = []

	error_counts = []

	julian_days = [x for x in range(julian_day_start, julian_day_end + 1)]
	#Wait for this Web request to complete, if it hasn't already.
	julian_start_gps = int(future_julian_start.result().content)

	SECONDS_PER_DAY = 86400

	low_eor0_count = high_eor0_count = low_eor1_count = high_eor1_count = error_count = 0

	prev_low_eor0_time = prev_high_eor0_time = prev_low_eor1_time = prev_high_eor1_time = 0

	utc_obsid_map_l0 = []
	utc_obsid_map_l1 = []
	utc_obsid_map_h0 = []
	utc_obsid_map_h1 = []

	prev_high_time = prev_low_time = 0

	for observation in response:
		obs_counts_index = 0
		try: #Most of the observation names end with the 7-digit Julian day, so we can just grab it from there.
			obs_counts_index = int(observation[1][-7:]) - julian_day_start
		except ValueError as ve:
			#If we couldn't get an integer from the observation name, we have to calculate the Julian day using the GPS time of the
			#start datetime and calculating how many days occurred between it and the observation in question.
			obs_counts_index = int((observation[0] - julian_start_gps) / SECONDS_PER_DAY)

						# Actual UTC time of the observation (for the graph)
		utc_millis = int((observation[0] - GPS_LEAP_SECONDS_OFFSET + GPS_UTC_DELTA) * 1000)

		obs_name = observation[1]

		try:
			ra_phase_center = int(observation[2])
		except TypeError as te:
			ra_phase_center = -1

		if 'low' in obs_name:
			if ra_phase_center == 0: # EOR0
				if utc_millis == prev_low_eor0_time:
					low_eor0_counts[-1][1] += 1
				else:
					low_eor0_counts.append([utc_millis, 1])
					prev_low_eor0_time = utc_millis
				low_eor0_count += 1
				utc_obsid_map_l0.append([utc_millis, int(observation[0])])
			elif ra_phase_center == 60: # EOR1
				if utc_millis == prev_low_eor1_time:
					low_eor1_counts[-1][1] += 1
				else:
					low_eor1_counts.append([utc_millis, 1])
					prev_low_eor1_time = utc_millis
				low_eor1_count += 1
				utc_obsid_map_l1.append([utc_millis, int(observation[0])])
		elif 'high' in obs_name:
			if ra_phase_center == 0: # EOR0
				if utc_millis == prev_high_eor0_time:
					high_eor0_counts[-1][1] += 1
				else:
					high_eor0_counts.append([utc_millis, 1])
					prev_high_eor0_time = utc_millis
				high_eor0_count += 1
				utc_obsid_map_h0.append([utc_millis, int(observation[0])])
			elif ra_phase_center == 60: # EOR1
				if utc_millis == prev_high_eor1_time:
					high_eor1_counts[-1][1] += 1
				else:
					high_eor1_counts.append([utc_millis, 1])
					prev_high_eor1_time = utc_millis
				high_eor1_count += 1
				utc_obsid_map_h1.append([utc_millis, int(observation[0])])

	prev_time = 0

	for error in obscontroller_response:
		utc_millis = int((error[0] - GPS_LEAP_SECONDS_OFFSET + GPS_UTC_DELTA) * 1000)
		if utc_millis == prev_time:
			error_counts[-1][1] += 1
		else:
			error_counts.append([utc_millis, 1])
			prev_time = utc_millis
		error_count += 1

	prev_time = 0

	for error in recvstatuspolice_response:
		utc_millis = int((error[0] - GPS_LEAP_SECONDS_OFFSET + GPS_UTC_DELTA) * 1000)
		if utc_millis == prev_time:
			error_counts[-1][1] += 1
		else:
			error_counts.append([utc_millis, 1])
			prev_time = utc_millis
		error_count += 1

	error_counts.sort(key=lambda error: error[0])

	return render_template('histogram.html', julian_days=julian_days,
        low_eor0_counts=low_eor0_counts, high_eor0_counts=high_eor0_counts,
        low_eor1_counts=low_eor1_counts, high_eor1_counts=high_eor1_counts,
        error_counts=error_counts, error_count=error_count,
        low_eor0_count=low_eor0_count, high_eor0_count=high_eor0_count,
        low_eor1_count=low_eor1_count, high_eor1_count=high_eor1_count,
        utc_obsid_map_l0=utc_obsid_map_l0, utc_obsid_map_l1=utc_obsid_map_l1,
        utc_obsid_map_h0=utc_obsid_map_h0, utc_obsid_map_h1=utc_obsid_map_h1,
        range_start=request.form['starttime'], range_end=request.form['endtime'])

@app.route('/error_table', methods = ['POST'])
def error_table():
	starttime = datetime.utcfromtimestamp(int(request.form['starttime']) / 1000).strftime('%Y-%m-%dT%H:%M:%SZ')

	endtime = datetime.utcfromtimestamp(int(request.form['endtime']) / 1000).strftime('%Y-%m-%dT%H:%M:%SZ')

	baseUTCToGPSURL = 'http://ngas01.ivec.org/metadata/tconv/?utciso='

	requestURLStart = baseUTCToGPSURL + starttime

	requestURLEnd = baseUTCToGPSURL + endtime

	session = FuturesSession()

	#Start the first Web service request in the background.
	future_start = session.get(requestURLStart)

	#The second request is started immediately.
	future_end = session.get(requestURLEnd)

	#Wait for the first request to complete, if it hasn't already.
	start_gps = int(future_start.result().content)

	#Wait for the second request to complete, if it hasn't already.
	end_gps = int(future_end.result().content)

	obscontroller_response = send_query(g.eor_db, '''SELECT reference_time, observation_number, comment
							FROM obscontroller_log
							WHERE reference_time >= {} AND reference_time < {}
							ORDER BY reference_time ASC'''.format(start_gps, end_gps)).fetchall()

	recvstatuspolice_response = send_query(g.eor_db, '''SELECT reference_time, observation_number, comment
							FROM recvstatuspolice_log
							WHERE reference_time >= {} AND reference_time < {}
							ORDER BY reference_time ASC'''.format(start_gps, end_gps)).fetchall()

	return render_template('error_table.html', obscontroller_error_list=obscontroller_response, recvstatuspolice_error_list=recvstatuspolice_response,
							start_time=starttime, end_time=endtime)

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
		setList = models.Set.query.filter(and_(models.Set.username == g.user.username))
		return render_template('profile.html', user=user, sets=setList)
	else:
		return redirect(url_for('login'))

@app.route('/get_sets', methods = ['POST'])
def get_sets():
	filter_type = request.form['filter_type']
	if (g.user is not None and g.user.is_authenticated()):
		if filter_type == 'all':
			setList = models.Set.query.all()

		elif filter_type == 'none':
			setList = None

		elif filter_type == 'filter_within_cur':
			startUTC = request.form['starttime']
			endUTC = request.form['endtime']
			baseUTCToGPSURL = 'http://ngas01.ivec.org/metadata/tconv/?utciso='
			requestURLStart = baseUTCToGPSURL + startUTC
			requestURLEnd = baseUTCToGPSURL + endUTC
			session = FuturesSession()
			#Start the first Web service request in the background.
			future_start = session.get(requestURLStart)
			#The second request is started immediately.
			future_end = session.get(requestURLEnd)
			#Wait for the first request to complete, if it hasn't already.
			start_gps = int(future_start.result().content)
			#Wait for the second request to complete, if it hasn't already.
			end_gps = int(future_end.result().content)
			setList = models.Set.query.filter(and_(models.Set.start >= start_gps, models.Set.end <= end_gps)).all()

		else:
			setList = models.Set.query.all()
		
		if setList is not None:
			return render_template('setList.html', sets=setList)
		else:
			return render_template('setList.html')
	else:
		return render_template('setList.html', logged_out=True)

@app.route('/save_comment', methods = ['POST'])
def save_comment():
	if (g.user is not None and g.user.is_authenticated()):
		set_id = request.form['set_id']
		comment_text = request.form['comment_text']

		theSet = models.Set.query.get(set_id)

		#now, add the comment
		com = models.Comment()
		com.text = comment_text
		com.username = g.user.username
		com.set_id = set_id

		theSet.comments.append(com)
		db.session.commit()

		return render_template('setView.html', comments=theSet.comments, set_id=theSet.id, setStart=theSet.start, setEnd=theSet.end)

@app.route('/delete_set', methods = ['POST'])
def delete_set():
	if (g.user is not None and g.user.is_authenticated()):
		set_name = request.form['set_name']
		user = models.User.query.get(g.user.username)

		theSet = models.Set.query.filter(and_(models.Set.name == set_name)).first()

		db.session.delete(theSet)
		db.session.commit()

		setList = models.Set.query.filter(and_(models.Set.username == g.user.username))
		return render_template('profile.html', user=user, sets=setList)
	else:
		return redirect(url_for('login'))
