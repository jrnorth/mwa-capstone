from app import views, models
from app.flask_app import app, db
from flask import request, g, make_response, jsonify

def insert_set_into_db(name, start, end, flagged_ranges):
    new_set = models.Set()
    new_set.username = g.user.username
    new_set.name = name
    new_set.start = start
    new_set.end = end
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

@app.route('/save_new_set', methods=['POST'])
def save_new_set():
    if (g.user is not None and g.user.is_authenticated()):
        request_content = request.get_json()

        name = request_content['name']

        if models.Set.query.filter(models.Set.name == name).count() > 0:
            return jsonify(duplicate_name=True)

        flagged_ranges = []

        i = 0

        for range in request_content['flaggedRanges']:
            flagged_ranges.append([])
            for pair in range:
                flagged_ranges[i].append(pair[1])
            i += 1

        insert_set_into_db(name, request_content['startObsId'],
            request_content['endObsId'], flagged_ranges)

        return jsonify()
    else:
        return make_response("You need to be logged in to save a set.", 401)

@app.route('/upload_set', methods=['POST'])
def upload_set():
    if (g.user is not None and g.user.is_authenticated()):
        set_name = request.form['set_name']

        if models.Set.query.filter(models.Set.name == set_name).count() > 0:
            return jsonify(duplicate_name=True)

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

        all_obs_ids_tuples = views.send_query(g.eor_db, '''SELECT starttime
                            FROM mwa_setting
                            WHERE starttime >= {} AND starttime <= {}
                            ORDER BY starttime ASC'''.format(good_obs_ids[0],
                            good_obs_ids[len(good_obs_ids) - 1])).fetchall()

        all_obs_ids = [tup[0] for tup in all_obs_ids_tuples]

        last_index = 0

        bad_ranges = []

        for good_obs_id in good_obs_ids:
            next_index = all_obs_ids.index(good_obs_id)
            if next_index > last_index:
                bad_ranges.append(all_obs_ids[last_index:next_index])

            last_index = next_index + 1

        insert_set_into_db(set_name, all_obs_ids[0], all_obs_ids[len(all_obs_ids) - 1], bad_ranges)

        return "OK"
    else:
        return make_response("You need to be logged in to upload a set.", 401)
