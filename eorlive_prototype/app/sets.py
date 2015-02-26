from app import views, models
from app.flask_app import app, db
from flask import request, g, make_response, jsonify

@app.route('/save_new_set', methods=['POST'])
def save_new_set():
    if (g.user is not None and g.user.is_authenticated()):
        request_content = request.get_json()

        name = request_content['name']

        if models.Set.query.filter(models.Set.name == name).count() > 0:
            return jsonify(duplicate_name=True)

        new_set = models.Set()

        new_set.username = g.user.username
        new_set.name = name
        new_set.start = request_content['startObsId']
        new_set.end = request_content['endObsId']
        db.session.add(new_set)
        db.session.flush()
        db.session.refresh(new_set) # So we can get the set's id

        flagged_ranges = request_content['flaggedRanges']

        for range in flagged_ranges:
            flagged_subset = models.FlaggedSubset()
            flagged_subset.set_id = new_set.id
            flagged_subset.start = range[0][1]
            flagged_subset.end = range[len(range) - 1][1]
            db.session.add(flagged_subset)
            db.session.flush()
            db.session.refresh(flagged_subset) # So we can get the id

            for pair in range: # Each entry is [utc_millis, obs_id]
                flagged_obs_id = models.FlaggedObsIds()
                flagged_obs_id.obs_id = pair[1]
                flagged_obs_id.flagged_subset_id = flagged_subset.id
                db.session.add(flagged_obs_id)

        db.session.commit()

        return jsonify()
    else:
        return make_response("You need to be logged in to save a set.", 401)
