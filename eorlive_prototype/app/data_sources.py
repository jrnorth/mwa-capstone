from flask import render_template, request, g, make_response, jsonify
import psycopg2
import os
import re
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
        return make_response("You must be logged in to use this feature.", 401)

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
        return make_response("You must be logged in to use this feature.", 401)

@app.route('/get_unsubscribed_data_sources')
def get_unsubscribed_data_sources():
    if g.user is not None and g.user.is_authenticated():
        all_data_sources = models.GraphDataSource.query.all()
        subscribed_data_sources = g.user.subscribed_data_sources

        unsubscribed_data_sources = list(set(all_data_sources) -\
            set(subscribed_data_sources))

        return render_template("unsubscribed_data_sources.html",
            unsubscribed_data_sources=unsubscribed_data_sources)
    else:
        return make_response("You must be logged in to use this feature.", 401)

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
        return make_response("You must be logged in to use this feature.", 401)

@app.route('/subscribe_to_data_source', methods = ['POST'])
def subscribe_to_data_source():
    if g.user is not None and g.user.is_authenticated():
        data_source_name = request.form['dataSource']

        data_source = models.GraphDataSource.query.filter(
            models.GraphDataSource.name == data_source_name).first()

        g.user.subscribed_data_sources.append(data_source)
        db.session.add(g.user)
        db.session.commit()
        return "Success"
    else:
        return make_response("You must be logged in to use this feature.", 401)

@app.route('/unsubscribe_from_data_source', methods = ['POST'])
def unsubscribe_from_data_source():
    if g.user is not None and g.user.is_authenticated():
        data_source_name = request.form['dataSource']

        data_source = models.GraphDataSource.query.filter(
            models.GraphDataSource.name == data_source_name).first()

        g.user.subscribed_data_sources.remove(data_source)
        try:
            g.user.active_data_sources.remove(data_source)
        except ValueError as e:
            #The user didn't have this as an active data source.
            print("Tried to remove an inactive data source")
        db.session.add(g.user)
        db.session.commit()
        return "Success"
    else:
        return make_response("You must be logged in to use this feature.", 401)

@app.route('/get_graph_types')
def get_graph_types():
    graph_types = models.GraphType.query.filter(models.GraphType.name != 'Obs_Err').all()
    return render_template('graph_type_list.html', graph_types=graph_types)

@app.route('/create_data_source', methods = ['POST'])
def create_data_source():
    if g.user is not None and g.user.is_authenticated():
        request_content = request.get_json()

        graph_type = request_content['graph_type']
        host = request_content['host']
        database = request_content['database']
        table = request_content['table']
        columns = request_content['columns']
        obs_column = request_content['obs_column']
        data_source_name = request_content['data_source_name']
        include_width_slider = request_content['include_width_slider']

        if not graph_type or not host or not database or not table or not columns\
            or not obs_column or not data_source_name:
            return jsonify(error=True, message="You need to fill out all the fields.")

        data_source_name = data_source_name.strip()
        if len(data_source_name) == 0:
            return jsonify(error=True, message="Name cannot be empty.")

        # The data source name (with spaces replaced by ಠ_ಠ) is used as
        # a JavaScript variable name and as an ID in HTML, so it needs
        # to obey the rules for those identifiers, minus a few
        # options such as $ since they would need to be escaped in
        # the HTML IDs.
        if not re.match(r'^[a-zA-Z_][0-9a-zA-Z_ ]*$', data_source_name):
            return jsonify(error=True, message="""Your data source name must
                start with a letter or _ that is followed by digits,
                letters, _, or spaces.""")

        #Is the data source name unique?
        if models.GraphDataSource.query.filter(models.GraphDataSource.name == data_source_name).first() is not None:
            return jsonify(error=True, message="The data source name must be unique.")

        try:
            db_conn = psycopg2.connect(database=database, host=host,
                user=os.environ['MWA_DB_USERNAME'], password=os.environ['MWA_DB_PW'])
        except Exception as e:
            return jsonify(error=True, message="Could not connect to that database.")

        table_response = db_utils.send_query(db_conn, """SELECT table_name
                                            FROM information_schema.tables
                                            WHERE table_name = '{}'
                                            AND table_schema='public'""".format(table)).fetchall()

        if len(table_response) == 0: #No results, so the table doesn't exist.
            db_conn.close()
            return jsonify(error=True, message="The table {} doesn't exist.".format(table))

        column_response = db_utils.send_query(db_conn, """SELECT column_name
                                            FROM information_schema.columns
                                            WHERE table_name = '{}'
                                            AND numeric_precision IS NOT NULL""".format(table)).fetchall()

        db_conn.close()

        columns_with_obs_column = list(columns)
        columns_with_obs_column.append(obs_column)

        for column in columns_with_obs_column: # So we can check for the existence of the obs column along with the
            column_exists = False              # others in the same loop.
            for returned_column in column_response:
                if returned_column[0] == column:
                    column_exists = True
                    break
            if not column_exists:
                return jsonify(error=True,
                    message="The column {} does not exist in that table or is not a numeric column.".format(column))

        projectid = False
        for returned_column in column_response:
            if returned_column[0] == 'projectid':
                projectid = True
                break

        graph_data_source = models.GraphDataSource()
        graph_data_source.name = data_source_name
        graph_data_source.graph_type = graph_type
        graph_data_source.host = host
        graph_data_source.database = database
        graph_data_source.table = table
        graph_data_source.obs_column = obs_column
        graph_data_source.projectid = projectid
        graph_data_source.width_slider = include_width_slider
        db.session.add(graph_data_source)
        db.session.flush()

        for column in columns:
            graph_data_source_column = models.GraphDataSourceColumn()
            graph_data_source_column.name = column
            graph_data_source_column.graph_data_source = data_source_name
            db.session.add(graph_data_source_column)

        g.user.subscribed_data_sources.append(graph_data_source)
        db.session.add(g.user)

        db.session.commit()

        return jsonify(error=False)
    else:
        return make_response("You must be logged in to use this feature.", 401)
