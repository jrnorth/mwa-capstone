from app import db_utils, models, histogram_utils
from app.flask_app import app, db
from flask import request, g, make_response, jsonify, render_template
from datetime import datetime

def insert_set_into_db(name, start, end, flagged_ranges, low_or_high,
        eor, total_data_hrs, flagged_data_hrs):
    new_set = models.Set()
    new_set.username = g.user.username
    new_set.name = name
    new_set.start = start
    new_set.end = end
    new_set.low_or_high = low_or_high
    new_set.eor = eor
    new_set.total_data_hrs = total_data_hrs
    new_set.flagged_data_hrs = flagged_data_hrs
    db.session.add(new_set)
    db.session.flush()
    db.session.refresh(new_set) # So we can get the set's id

    for range in flagged_ranges:
        flagged_subset = models.FlaggedSubset()
        flagged_subset.set_id = new_set.id
        flagged_subset.start = range[0]
        flagged_subset.end = range[len(range) - 1]
        db.session.add(flagged_subset)
        db.session.flush()
        db.session.refresh(flagged_subset) # So we can get the id

        for obs_id in range:
            flagged_obs_id = models.FlaggedObsIds()
            flagged_obs_id.obs_id = obs_id
            flagged_obs_id.flagged_subset_id = flagged_subset.id
            db.session.add(flagged_obs_id)

    db.session.commit()

def is_obs_flagged(obs_id, flagged_ranges):
    for flagged_range in flagged_ranges:
        if obs_id >= flagged_range[0] and obs_id <= flagged_range[len(flagged_range) - 1]:
            return True
    return False

def get_data_hours_in_set(start, end, low_or_high, eor, flagged_ranges):
    total_data_hrs = flagged_data_hrs = 0

    low_high_clause, eor_clause = db_utils.get_lowhigh_and_eor_clauses(low_or_high, eor)

    all_obs_ids_tuples = db_utils.send_query(g.eor_db, '''SELECT starttime, stoptime
                            FROM mwa_setting
                            WHERE starttime >= {} AND starttime <= {}
                            AND projectid='G0009'
                            {}
                            {}
                            ORDER BY starttime ASC'''.format(start, end, low_high_clause, eor_clause)).fetchall()

    for obs in all_obs_ids_tuples:
        obs_id = obs[0]
        data_hrs = (obs[1] - obs_id) / 3600
        total_data_hrs += data_hrs
        if is_obs_flagged(obs_id, flagged_ranges):
            flagged_data_hrs += data_hrs

    return (total_data_hrs, flagged_data_hrs)

@app.route('/save_new_set', methods=['POST'])
def save_new_set():
    if (g.user is not None and g.user.is_authenticated()):
        request_content = request.get_json()

        name = request_content['name']

        if name is None:
            return jsonify(error=True, message="Name cannot be empty.")

        name = name.strip()

        if len(name) == 0:
            return jsonify(error=True, message="Name cannot be empty.")

        if models.Set.query.filter(models.Set.name == name).count() > 0:
            return jsonify(error=True, message="Name must be unique.")

        flagged_ranges = []

        i = 0

        for range in request_content['flaggedRanges']:
            flagged_ranges.append([])
            for pair in range:
                flagged_ranges[i].append(pair[1])
            i += 1

        start_gps = request_content['startObsId']
        end_gps = request_content['endObsId']
        low_or_high = request_content['lowOrHigh']
        eor = request_content['eor']

        total_data_hrs, flagged_data_hrs = get_data_hours_in_set(
            start_gps, end_gps, low_or_high, eor, flagged_ranges)

        insert_set_into_db(name, start_gps, end_gps, flagged_ranges,
            low_or_high, 'EOR' + eor, total_data_hrs, flagged_data_hrs)

        return jsonify()
    else:
        return make_response("You need to be logged in to save a set.", 401)

@app.route('/upload_set', methods=['POST'])
def upload_set():
    if (g.user is not None and g.user.is_authenticated()):
        set_name = request.form['set_name']

        if set_name is None:
            return jsonify(error=True, message="Name cannot be empty.")

        set_name = set_name.strip()

        if len(set_name) == 0:
            return jsonify(error=True, message="Name cannot be empty.")

        if models.Set.query.filter(models.Set.name == set_name).count() > 0:
            return jsonify(error=True, message="Name must be unique.")

        f = request.files['file']

        good_obs_ids = []

        for line in f.stream:
            line = str(line.decode("utf-8").strip())
            if line == '':
                continue
            try:
                obs_id = int(line)
                good_obs_ids.append(obs_id)
            except ValueError as ve:
                return jsonify(data_error='Invalid content in file: ' + line)

        good_obs_ids.sort()

        start_gps = good_obs_ids[0]
        end_gps = good_obs_ids[len(good_obs_ids) - 1]

        all_obs_ids_tuples = db_utils.send_query(g.eor_db, '''SELECT starttime
                            FROM mwa_setting
                            WHERE starttime >= {} AND starttime <= {}
                            ORDER BY starttime ASC'''
                            .format(start_gps, end_gps)).fetchall()

        all_obs_ids = [tup[0] for tup in all_obs_ids_tuples]

        last_index = 0

        bad_ranges = []

        for good_obs_id in good_obs_ids:
            next_index = all_obs_ids.index(good_obs_id)
            if next_index > last_index:
                bad_ranges.append(all_obs_ids[last_index:next_index])

            last_index = next_index + 1

        low_or_high = request.form['low_or_high']
        eor = request.form['eor']

        total_data_hrs, flagged_data_hrs = get_data_hours_in_set(
            start_gps, end_gps, low_or_high, eor, bad_ranges)

        insert_set_into_db(set_name, start_gps, end_gps, bad_ranges,
            low_or_high, eor, total_data_hrs, flagged_data_hrs)

        return "OK"
    else:
        return make_response("You need to be logged in to upload a set.", 401)

@app.route('/download_set')
def download_set():
    set_id = request.args['set_id']

    the_set = models.Set.query.filter(models.Set.id == set_id).first()

    if the_set is not None:
        flagged_subsets = models.FlaggedSubset.query.filter(models.FlaggedSubset.set_id == the_set.id).all()

        all_obs_ids_tuples = db_utils.send_query(g.eor_db, '''SELECT starttime
                            FROM mwa_setting
                            WHERE starttime >= {} AND starttime <= {}
                            ORDER BY starttime ASC'''.format(the_set.start,
                            the_set.end)).fetchall()

        all_obs_ids = [tup[0] for tup in all_obs_ids_tuples]

        good_obs_ids_text_file = ""

        for obs_id in all_obs_ids:
            good = True # assume obs_id is good
            for flagged_subset in flagged_subsets:
                if obs_id >= flagged_subset.start and obs_id <= flagged_subset.end: # obs_id is flagged, so it's not good
                    good = False
                    break
            if good:
                good_obs_ids_text_file += str(obs_id) + '\n'

        response = make_response(good_obs_ids_text_file)
        filename = the_set.name.replace(' ', '_') + ".txt"
        response.headers["Content-Disposition"] = "attachment; filename=" + filename
        return response
    else:
        return make_response("That set wasn't found.", 500)

@app.route('/data_summary_table', methods=['POST'])
def data_summary_table():
    starttime = request.form['starttime']
    endtime = request.form['endtime']

    startdatetime = datetime.strptime(starttime, '%Y-%m-%dT%H:%M:%SZ')
    enddatetime = datetime.strptime(endtime, '%Y-%m-%dT%H:%M:%SZ')

    start_gps, end_gps = db_utils.get_gps_from_datetime(startdatetime, enddatetime)

    response = db_utils.send_query(g.eor_db, '''SELECT starttime, stoptime, obsname, ra_phase_center
                    FROM mwa_setting
                    WHERE starttime >= {} AND starttime <= {}
                    AND projectid='G0009'
                    ORDER BY starttime ASC'''.format(start_gps, end_gps)).fetchall()

    low_eor0_count = low_eor1_count = high_eor0_count = high_eor1_count = 0
    low_eor0_hours = low_eor1_hours = high_eor0_hours = high_eor1_hours = 0

    for observation in response:
        start_time = observation[0]
        stop_time = observation[1]
        obs_name = observation[2]

        try:
            ra_phase_center = int(observation[3])
        except TypeError as te:
            ra_phase_center = -1

        data_hours = (stop_time - start_time) / 3600

        if 'low' in obs_name:
            if ra_phase_center == 0:
                low_eor0_count += 1
                low_eor0_hours += data_hours
            elif ra_phase_center == 60:
                low_eor1_count += 1
                low_eor1_hours += data_hours
        elif 'high' in obs_name:
            if ra_phase_center == 0:
                high_eor0_count += 1
                high_eor0_hours += data_hours
            elif ra_phase_center == 60:
                high_eor1_count += 1
                high_eor1_hours += data_hours

    error_counts, error_count = histogram_utils.get_error_counts(start_gps, end_gps)

    return render_template("summary_table.html", error_count=error_count,
        low_eor0_count=low_eor0_count, high_eor0_count=high_eor0_count,
        low_eor1_count=low_eor1_count, high_eor1_count=high_eor1_count,
        low_eor0_hours=low_eor0_hours, high_eor0_hours=high_eor0_hours,
        low_eor1_hours=low_eor1_hours, high_eor1_hours=high_eor1_hours)

@app.route('/get_filters')
def get_filters():
    users = models.User.query.all()
    return render_template("filters.html", users=users)
