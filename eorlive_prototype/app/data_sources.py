from flask import render_template, request, g, make_response
import psycopg2
import os
from app.flask_app import app, db
from app import db_utils, models

@app.route('/get_tables', methods = ['POST'])
def get_tables():
    if g.user is not None and g.user.is_authenticated():
        hostname = request.form['hostname']
        database = request.form['database']

        try:
            db_conn = psycopg2.connect(database=database, host=hostname,
                user=os.environ['MWA_DB_USERNAME'], password=os.environ['MWA_DB_PW'])
        except Exception as e:
            return "Can't connect to database"

        table_tuples = db_utils.send_query(db_conn, """SELECT table_name
                                                    FROM information_schema.tables
                                                    WHERE table_schema='public'
                                                    ORDER BY table_name""").fetchall()

        db_conn.close()

        return render_template("table_list.html", table_tuples=table_tuples)
    else:
        return make_response("You must be logged in to use this feature.", 401)

@app.route('/get_columns', methods = ['POST'])
def get_columns():
    if g.user is not None and g.user.is_authenticated():
        hostname = request.form['hostname']
        database = request.form['database']
        table = request.form['table']

        try:
            db_conn = psycopg2.connect(database=database, host=hostname,
                user=os.environ['MWA_DB_USERNAME'], password=os.environ['MWA_DB_PW'])
        except Exception as e:
            return "Can't connect to database"

        column_tuples = db_utils.send_query(db_conn, """SELECT column_name
                                                    FROM information_schema.columns
                                                    WHERE table_name = '{}'
                                                    AND numeric_precision IS NOT NULL""".format(table)).fetchall()

        db_conn.close()

        return render_template("column_list.html", column_tuples=column_tuples)
    else:
        return make_response("You must be logged in to use this feature.", 401);

@app.route('/get_users_data_sources')
def get_users_data_sources():
    if g.user is not None and g.user.is_authenticated():
        active_data_sources = g.user.active_data_sources
        subscribed_but_inactive_data_sources =\
            list(set(g.user.subscribed_data_sources) - set(active_data_sources))

        return render_template("data_sources.html",
            subscribed_but_inactive_data_sources=subscribed_but_inactive_data_sources,
            active_data_sources=g.user.active_data_sources)
    else:
        return make_response("You must be logged in to use this feature.", 401);

@app.route('/get_unsubscribed_data_sources')
def get_unsubscribed_data_sources():
    if g.user is not None and g.user.is_authenticated():
        all_data_sources = models.GraphDataSource.query.all()
        subscribed_data_sources = g.user.subscribed_data_sources

        unsubscribed_data_sources = list(set(all_data_sources) -\
            set(subscribed_data_sources))

        return render_template("data_sources.html",
            unsubscribed_data_sources=unsubscribed_data_sources)
    else:
        return make_response("You must be logged in to use this feature.", 401);

@app.route('/update_active_data_sources', methods = ['POST'])
def update_active_data_sources():
    if g.user is not None and g.user.is_authenticated():
        request_content = request.get_json()
        new_active_data_sources_names = request_content['activeDataSources']

        new_active_data_sources = models.GraphDataSource.query.filter(
            models.GraphDataSource.name.in_(new_active_data_sources_names)).all()
        current_active_data_sources = g.user.active_data_sources
        active_to_remove = list(set(current_active_data_sources) -\
            set(new_active_data_sources))
        active_to_add = list(set(new_active_data_sources) -\
            set(current_active_data_sources))

        for active_data_source in active_to_remove:
            g.user.active_data_sources.remove(active_data_source)

        for active_data_source in active_to_add:
            g.user.active_data_sources.append(active_data_source)

        db.session.add(g.user)
        db.session.commit()
        return "Success"
    else:
        return make_response("You must be logged in to use this feature.", 401);
