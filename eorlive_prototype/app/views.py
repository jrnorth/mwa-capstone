from flask import render_template, flash, redirect, session, url_for, request, g, make_response
from flask.ext.login import login_user, logout_user, current_user, login_required
from app.flask_app import app, lm, db
from app import models, db_utils, histogram_utils
import requests
import json
import hashlib
from sqlalchemy import and_
from datetime import datetime, timedelta
import psycopg2
import os

@app.route('/')
@app.route('/index')
@app.route('/index/set/<setName>')
@app.route('/set/<setName>')
def index(setName = None):
    # GET is the default request method.
    # Since we're using GET, we have to access arguments by request.args.get() rather than request.form[]
    if setName is not None:
        theSet = models.Set.query.filter(models.Set.name == setName).first()

        if theSet is None:
            return render_template('index.html')

        observation_counts = histogram_utils.get_observation_counts(theSet.start, theSet.end,
            theSet.low_or_high, theSet.eor)
        error_counts = histogram_utils.get_error_counts(theSet.start, theSet.end)[0]
        plot_bands = histogram_utils.get_plot_bands(theSet)

        start_datetime, end_datetime = db_utils.get_datetime_from_gps(theSet.start, theSet.end)

        formatted_start = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
        formatted_end = end_datetime.strftime('%Y-%m-%d %H:%M:%S')

        if (g.user is not None and g.user.is_authenticated()):
            return render_template('setView.html', setName=theSet.name, set_id=theSet.id,
                setStart=theSet.start, setEnd=theSet.end, observation_counts=observation_counts,
                error_counts=error_counts, plot_bands=plot_bands, range_end=theSet.end,
                formatted_start=formatted_start, formatted_end=formatted_end,
                low_or_high=theSet.low_or_high, eor=theSet.eor, creator=theSet.username,
                total_data_hrs=theSet.total_data_hrs, flagged_data_hrs=theSet.flagged_data_hrs)
        else: #logged out view
            return render_template('setView.html', setName=theSet.name, set_id=theSet.id, setStart=theSet.start,
                setEnd=theSet.end, logged_out=True, observation_counts=observation_counts, error_counts=error_counts,
                plot_bands=plot_bands, range_end=theSet.end, formatted_start=formatted_start,
                formatted_end=formatted_end, low_or_high=theSet.low_or_high,
                eor=theSet.eor, creator=theSet.username, total_data_hrs=theSet.total_data_hrs,
                flagged_data_hrs=theSet.flagged_data_hrs)
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

@app.route('/histogram_data', methods = ['GET'])
def histogram_data():
    start_time = request.args.get('starttime')
    end_time = request.args.get('endtime')

    startdatetime = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%SZ')

    enddatetime = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%SZ')

    start_gps, end_gps = db_utils.get_gps_from_datetime(startdatetime, enddatetime)

    response = db_utils.send_query(g.eor_db, '''SELECT starttime, stoptime, obsname, ra_phase_center
                    FROM mwa_setting
                    WHERE starttime >= {} AND starttime <= {}
                    AND projectid='G0009'
                    ORDER BY starttime ASC'''.format(start_gps, end_gps)).fetchall()

    low_eor0_counts = []

    high_eor0_counts = []

    low_eor1_counts = []

    high_eor1_counts = []

    error_counts, error_count = histogram_utils.get_error_counts(start_gps, end_gps)

    utc_obsid_map_l0 = []
    utc_obsid_map_l1 = []
    utc_obsid_map_h0 = []
    utc_obsid_map_h1 = []

    GPS_LEAP_SECONDS_OFFSET, GPS_UTC_DELTA = db_utils.get_gps_utc_constants()

    for observation in response:
                        # Actual UTC time of the observation (for the graph)
        utc_millis = int((observation[0] - GPS_LEAP_SECONDS_OFFSET + GPS_UTC_DELTA) * 1000)

        obs_name = observation[2]

        try:
            ra_phase_center = int(observation[3])
        except TypeError as te:
            ra_phase_center = -1

        if 'low' in obs_name:
            if ra_phase_center == 0: # EOR0
                low_eor0_counts.append([utc_millis, 1])
                utc_obsid_map_l0.append([utc_millis, int(observation[0])])
            elif ra_phase_center == 60: # EOR1
                low_eor1_counts.append([utc_millis, 1])
                utc_obsid_map_l1.append([utc_millis, int(observation[0])])
        elif 'high' in obs_name:
            if ra_phase_center == 0: # EOR0
                high_eor0_counts.append([utc_millis, 1])
                utc_obsid_map_h0.append([utc_millis, int(observation[0])])
            elif ra_phase_center == 60: # EOR1
                high_eor1_counts.append([utc_millis, 1])
                utc_obsid_map_h1.append([utc_millis, int(observation[0])])

    return render_template('histogram.html',
        low_eor0_counts=low_eor0_counts, high_eor0_counts=high_eor0_counts,
        low_eor1_counts=low_eor1_counts, high_eor1_counts=high_eor1_counts,
        error_counts=error_counts, utc_obsid_map_l0=utc_obsid_map_l0,
        utc_obsid_map_l1=utc_obsid_map_l1, utc_obsid_map_h0=utc_obsid_map_h0,
        utc_obsid_map_h1=utc_obsid_map_h1, range_start=start_time,
        range_end=end_time)

@app.route('/qs_data')
def qs_data():
    start_time = request.args.get('starttime')
    end_time = request.args.get('endtime')

    start_datetime = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%SZ')
    end_datetime = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%SZ')

    start_gps, end_gps = db_utils.get_gps_from_datetime(start_datetime, end_datetime)

    response = db_utils.send_query(g.eor_00, '''SELECT obsid, window_x, window_y,
                                    wedge_res_x, wedge_res_y, gal_wedge_x,
                                    gal_wedge_y, ptsrc_wedge_x, ptsrc_wedge_y
                                    FROM qs
                                    WHERE wedge_timestamp IS NOT NULL
                                    AND obsid >= {} AND obsid <= {}
                                    ORDER BY obsid ASC'''.format(start_gps, end_gps)).fetchall()

    GPS_LEAP_SECONDS_OFFSET, GPS_UTC_DELTA = db_utils.get_gps_utc_constants()

    window_x = []
    window_y = []
    wedge_res_x = []
    wedge_res_y = []
    gal_wedge_x = []
    gal_wedge_y = []
    ptsrc_wedge_x = []
    ptsrc_wedge_y = []

    for row in response:
                    # Actual UTC time of the observation (for the graph)
        utc_millis = int((row[0] - GPS_LEAP_SECONDS_OFFSET + GPS_UTC_DELTA) * 1000)

        window_x.append([utc_millis, row[1]])
        window_y.append([utc_millis, row[2]])
        wedge_res_x.append([utc_millis, row[3]])
        wedge_res_y.append([utc_millis, row[4]])
        gal_wedge_x.append([utc_millis, row[5]])
        gal_wedge_y.append([utc_millis, row[6]])
        ptsrc_wedge_x.append([utc_millis, row[7]])
        ptsrc_wedge_y.append([utc_millis, row[8]])

    data = {
        "window_x": window_x,
        "window_y": window_y,
        "wedge_res_x": wedge_res_x,
        "wedge_res_y": wedge_res_y,
        "gal_wedge_x": gal_wedge_x,
        "gal_wedge_y": gal_wedge_y,
        "ptsrc_wedge_x": ptsrc_wedge_x,
        "ptsrc_wedge_y": ptsrc_wedge_y
    };

    return render_template("qs_graph.html", data=data)

@app.route('/error_table', methods = ['POST'])
def error_table():
    starttime = datetime.utcfromtimestamp(int(request.form['starttime']) / 1000)

    endtime = datetime.utcfromtimestamp(int(request.form['endtime']) / 1000)

    start_gps, end_gps = db_utils.get_gps_from_datetime(starttime, endtime)

    obscontroller_response = db_utils.send_query(g.eor_db, '''SELECT reference_time, observation_number, comment
                            FROM obscontroller_log
                            WHERE reference_time >= {} AND reference_time < {}
                            ORDER BY reference_time ASC'''.format(start_gps, end_gps)).fetchall()

    recvstatuspolice_response = db_utils.send_query(g.eor_db, '''SELECT reference_time, observation_number, comment
                            FROM recvstatuspolice_log
                            WHERE reference_time >= {} AND reference_time < {}
                            ORDER BY reference_time ASC'''.format(start_gps, end_gps)).fetchall()

    return render_template('error_table.html', obscontroller_error_list=obscontroller_response,
                            recvstatuspolice_error_list=recvstatuspolice_response,
                            start_time=starttime.strftime('%Y-%m-%dT%H:%M:%SZ'),
                            end_time=endtime.strftime('%Y-%m-%dT%H:%M:%SZ'))

@app.before_request
def before_request():
    g.user = current_user
    try :
        g.eor_db = psycopg2.connect(database='mwa', host='eor-db.mit.edu',
            user=os.environ['MWA_DB_USERNAME'], password=os.environ['MWA_DB_PW'])
        g.eor_00 = psycopg2.connect(database='mwa_qc', host='eor-00.mit.edu',
            user=os.environ['MWA_DB_USERNAME'], password=os.environ['MWA_DB_PW'])
    except Exception as e:
        print("Can't connect to database - %s" % e)

@app.teardown_request
def teardown_request(exception):
    eor_db = getattr(g, 'eor_db', None)
    if eor_db is not None:
        eor_db.close()

    eor_00 = getattr(g, 'eor_00', None)
    if eor_00 is not None:
        eor_00.close()

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
        setList = models.Set.query.filter(models.Set.username == g.user.username)
        return render_template('profile.html', user=user, sets=setList)
    else:
        return redirect(url_for('login'))

@app.route('/get_sets', methods = ['POST'])
def get_sets():
    if (g.user is not None and g.user.is_authenticated()):
        request_content = request.get_json()
        set_controls = request_content['set_controls']
        filter_type = set_controls['filter']
        eor = set_controls['eor']
        high_low = set_controls['high_low']
        sort = set_controls['sort']

        query = models.Set.query

        if filter_type:
            if filter_type == 'yours':
                query = query.filter(models.Set.username == g.user.username)
            elif filter_type == 'filter_within_cur':
                startUTC = request_content['starttime']
                endUTC = request_content['endtime']
                start_datetime = datetime.strptime(startUTC, '%Y-%m-%dT%H:%M:%SZ')
                end_datetime = datetime.strptime(endUTC, '%Y-%m-%dT%H:%M:%SZ')
                start_gps, end_gps = db_utils.get_gps_from_datetime(start_datetime, end_datetime)
                query = query.filter(and_(models.Set.start >= start_gps, models.Set.end <= end_gps))

        if eor:
            query = query.filter(models.Set.eor == eor) # eor is 'EOR0' or 'EOR1', which are the values used in the DB

        if high_low:
            query = query.filter(models.Set.low_or_high == high_low) # high_low is 'high' or 'low', which are the
                                                                     # values used in the DB

        if sort:
            if sort == 'hours':
                query = query.order_by(models.Set.total_data_hrs.desc())
            elif sort == 'time':
                query = query.order_by(models.Set.created_on.desc())

        setList = query.all()

        if setList is not None:
            return render_template('setList.html', sets=setList)
        else:
            return render_template('setList.html')
    else:
        return render_template('setList.html', logged_out=True)

@app.route('/delete_set', methods = ['POST'])
def delete_set():
    if (g.user is not None and g.user.is_authenticated()):
        set_name = request.form['set_name']
        user = models.User.query.get(g.user.username)

        theSet = models.Set.query.filter(models.Set.name == set_name).first()

        db.session.delete(theSet)
        db.session.commit()

        setList = models.Set.query.filter(models.Set.username == g.user.username)
        return render_template('profile.html', user=user, sets=setList)
    else:
        return redirect(url_for('login'))
