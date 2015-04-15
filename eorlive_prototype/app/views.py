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
import re

@app.route('/')
@app.route('/index')
@app.route('/index/set/<setName>')
@app.route('/set/<setName>')
def index(setName = None):
    active_data_sources = []

    if g.user is not None and g.user.is_authenticated():
        active_data_sources = g.user.active_data_sources

    if setName is not None:
        the_set = models.Set.query.filter(models.Set.name == setName).first()

        if the_set is not None:
            start_datetime, end_datetime = db_utils.get_datetime_from_gps(
                the_set.start, the_set.end)
            start_time_str_full = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            end_time_str_full = end_datetime.strftime('%Y-%m-%d %H:%M:%S')
            start_time_str_short = start_datetime.strftime('%Y/%m/%d %H:%M')
            end_time_str_short = end_datetime.strftime('%Y/%m/%d %H:%M')

            return render_template('index.html', the_set=the_set,
                start_time_str_full=start_time_str_full,
                end_time_str_full=end_time_str_full,
                start_time_str_short=start_time_str_short,
                end_time_str_short=end_time_str_short,
                active_data_sources=active_data_sources)

    return render_template('index.html', active_data_sources=active_data_sources)

@app.route('/get_graph')
def get_graph():
    graph_type_str = request.args.get('graphType')
    if graph_type_str is None:
        return make_response('No graph type', 500)

    data_source_str = request.args.get('dataSource')
    if data_source_str is None:
        return make_response('No data source', 500)

    data_source = models.GraphDataSource.query.filter(models.GraphDataSource.name == data_source_str).first()

    set_str = request.args.get('set')

    template_name = "js/" + graph_type_str.lower() + ".js"

    if set_str is None: # There should be a date range instead.
        start_time_str = request.args.get('start')
        end_time_str = request.args.get('end')
        if start_time_str is None or end_time_str is None:
            return make_response('No date range specified', 500)

        start_datetime = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%SZ')

        end_datetime = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M:%SZ')

        start_gps, end_gps = db_utils.get_gps_from_datetime(start_datetime, end_datetime)

        if graph_type_str == 'Obs_Err':
            return histogram_utils.get_obs_err_histogram(start_gps, end_gps,
                start_time_str, end_time_str)
        else:
            graph_data = db_utils.get_graph_data(data_source_str, start_gps, end_gps, None)
            data_source_str_nospace = data_source_str.replace(' ', '_')
            return render_template('graph.html', graph_type_str=graph_type_str.lower(),
                data_source_str=data_source_str, graph_data=graph_data,
                plot_bands=[], template_name=template_name, is_set=False,
                data_source_str_nospace=data_source_str_nospace,
                start_time_str=start_datetime.strftime('%Y-%m-%d %H:%M'),
                end_time_str=end_datetime.strftime('%Y-%m-%d %H:%M'),
                width_slider=data_source.width_slider)
    else:
        the_set = models.Set.query.filter(models.Set.name == set_str).first()
        if the_set is None:
            return make_response('Set not found', 500)

        plot_bands = histogram_utils.get_plot_bands(the_set)

        if graph_type_str == 'Obs_Err':
            observation_counts = histogram_utils.get_observation_counts(
                the_set.start, the_set.end, the_set.low_or_high, the_set.eor)
            error_counts = histogram_utils.get_error_counts(the_set.start, the_set.end)[0]
            start_datetime, end_datetime = db_utils.get_datetime_from_gps(
                the_set.start, the_set.end)
            start_time_str_full = start_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_time_str_full = end_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
            return render_template('setView.html', the_set=the_set,
                observation_counts=observation_counts, error_counts=error_counts,
                plot_bands=plot_bands, start_time_str_full=start_time_str_full,
                end_time_str_full=end_time_str_full)
        else:
            graph_data = db_utils.get_graph_data(data_source_str, the_set.start, the_set.end, the_set)
            data_source_str_nospace = data_source_str.replace(' ', '_')
            return render_template('graph.html', graph_type_str=graph_type_str.lower(),
                data_source_str=data_source_str, graph_data=graph_data, plot_bands=plot_bands,
                template_name=template_name, is_set=True, data_source_str_nospace=data_source_str_nospace,
                width_slider=data_source.width_slider)

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

@app.route('/signup', methods= ['GET', 'POST'])
def signup():
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        password2 = request.form['password2'].strip()
        email = request.form['email'].strip()
        fname = request.form['fname'].strip()
        lname = request.form['lname'].strip()

        testU = models.User.query.get(username)

        if password != password2:
            error = "Passwords must be the same."
        elif testU is not None:
            error = "That username is already in use."
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            error = "That email address is not correct."
        else:
            real_pass = password.encode('UTF-8')

            new_user = models.User(username, hashlib.sha512(real_pass).hexdigest(), email, fname, lname)
            db.session.add(new_user)
            db.session.flush()
            db.session.refresh(new_user)
            db.session.commit()

            u = models.User.query.get(username)
            login_user(u)
            flash('You were logged in')
            return redirect(url_for('index'))
    return render_template('signup.html', error=error)

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

@app.route('/user_page')
def user_page():
    if (g.user is not None and g.user.is_authenticated()):
        user = models.User.query.get(g.user.username)
        userList = models.User.query.all()
        setList = models.Set.query.all()
        return render_template('user_page.html', theUser=user, userList=userList, setList=setList)
    else:
        return redirect(url_for('login'))

@app.route('/delete_user', methods=['POST'])
def delete_user():
    if (g.user is not None and g.user.is_authenticated()):
        username = request.form['username']
        action = request.form['action']

        setList = models.Set.query.filter(models.Set.username == username)

        for aSet in setList:
            theSet = models.Set.query.filter(models.Set.id == aSet.id).first()
            if action == 'transfer':
                theSet.username = g.user.username
            else: #destroy, cascade deletion
                db.session.delete(theSet)
            db.session.commit()

        u = models.User.query.filter(models.User.username == username).first()

        db.session.delete(u)
        db.session.commit()

        return redirect(url_for('user_page'))

@app.route('/get_sets', methods = ['POST'])
def get_sets():
    if (g.user is not None and g.user.is_authenticated()):
        request_content = request.get_json()
        set_controls = request_content['set_controls']
        username = set_controls['user']
        eor = set_controls['eor']
        high_low = set_controls['high_low']
        sort = set_controls['sort']
        ranged = set_controls['ranged']

        query = models.Set.query

        if username:
            query = query.filter(models.Set.username == username)

        if eor:
            query = query.filter(models.Set.eor == eor) # eor is 'EOR0' or 'EOR1', which are the values used in the DB

        if high_low:
            query = query.filter(models.Set.low_or_high == high_low) # high_low is 'high' or 'low', which are the
                                                                     # values used in the DB

        if ranged:
            start_utc = request_content['starttime']
            end_utc = request_content['endtime']
            start_datetime = datetime.strptime(start_utc, '%Y-%m-%dT%H:%M:%SZ')
            end_datetime = datetime.strptime(end_utc, '%Y-%m-%dT%H:%M:%SZ')
            start_gps, end_gps = db_utils.get_gps_from_datetime(start_datetime, end_datetime)
            query = query.filter(and_(models.Set.start >= start_gps,
                                    models.Set.end <= end_gps))

        if sort:
            if sort == 'hours':
                query = query.order_by(models.Set.total_data_hrs.desc())
            elif sort == 'time':
                query = query.order_by(models.Set.created_on.desc())

        setList = query.all()

        include_delete_buttons = request_content['includeDeleteButtons']

        return render_template('setList.html', sets=setList,
            include_delete_buttons=include_delete_buttons)
    else:
        return render_template('setList.html', logged_out=True)

@app.route('/delete_set', methods = ['POST'])
def delete_set():
    if (g.user is not None and g.user.is_authenticated()):
        set_id = request.form['set_id']

        theSet = models.Set.query.filter(models.Set.id == set_id).first()

        db.session.delete(theSet)
        db.session.commit()
        return "Success"
    else:
        return redirect(url_for('login'))
